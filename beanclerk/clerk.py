"""Clerk operations.

This module provides operations consumed by the CLI.

Todo:
    * check each new txn has `id` in its metadata (without this we can't check
    for duplicates)
    * handle exceptions
    * Python docs recommend to use utf-8 encoding for reading and writing files
    * validate txns coming from importers:
        * check that txns have only 1 posting
        * check that txns have id in their metadata
    * Test fn append_entry_to_file.
    * Check txns from an importer have only 1 posting (don't implement this until
    a more complex use case - like importing from an crypto exchange - is implemented).
    * Try out Beancount v3: https://groups.google.com/g/beancount/c/LVBQ4cD0PYc.
    According to the thread, it should be stable enough.
"""

import copy
import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import beancount.core.data as bean_data
import beancount.core.realization
import beancount.loader
import beancount.parser.printer
import rich
import rich.prompt

from . import bean_helpers, config, exceptions, importers


def find_last_import_date(
    entries: list[bean_data.Directive], account_name: str
) -> date | None:
    """Return date of the last imported transaction, or None if not found.

    This function searches for the latest transaction with `id` key in its
    metadata. Entries must be properly ordered.

    Args:
        entries (list[beancount.core.data.Directive]): a list of Beancount directives
        account_name (str): Beancount account name

    Returns:
        date | None
    """
    bean_helpers.validate_account_name(account_name)
    txn_postings = bean_helpers.filter_entries(
        beancount.core.realization.postings_by_account(entries)[account_name],
        bean_data.TxnPosting,
    )
    for txn_posting in reversed(list(txn_postings)):  # latest first
        if txn_posting.txn.meta.get("id") is not None:
            return txn_posting.txn.date
    return None


def transaction_exists(
    entries: list[bean_data.Directive],
    account_name: str,
    txn_id: str,
) -> bool:
    """Return True if the account has a transaction with the given ID.

    Args:
        entries (list[beancount.core.data.Directive]): a list of Beancount directives
        account_name (str): Beancount account name
        txn_id (str): transaction ID (`id` key in its metadata)

    Returns:
        bool
    """
    bean_helpers.validate_account_name(account_name)
    txn_postings = bean_helpers.filter_entries(
        beancount.core.realization.postings_by_account(entries)[account_name],
        bean_data.TxnPosting,
    )
    return any(txn_posting.txn.meta.get("id") == txn_id for txn_posting in txn_postings)


def compute_balance(
    entries: list[bean_data.Directive],
    account_name: str,
    currency: str,
) -> bean_data.Amount:
    """Return account balance for the given account and currency.

    If the account does not exist, it returns Amount 0.

    Args:
        entries (list[beancount.core.data.Directive]): a list of Beancount directives
        account_name (str): Beancount account name
        currency (str): currency ISO code (e.g. 'USD')

    Returns:
        Amount: account balance
    """
    bean_helpers.validate_account_name(account_name)
    if not re.match(r"^[A-Z]{3}$", currency):
        raise ValueError(f"'{currency}' is not a valid currency code")
    return beancount.core.realization.compute_postings_balance(
        beancount.core.realization.postings_by_account(entries)[account_name],
    ).get_currency_units(currency)


def find_categorization_rule(
    transaction: bean_data.Transaction,
    cfg: config.Config,
) -> config.CategorizationRule | None:
    """Return a categorization rule matching the given transaction.

    If no rule matches the transaction, the user is prompted to choose
    an action to resolve the situation. The user may also choose not
    to categorize the transaction, None is returned then.

    Args:
        transaction (beancount.core.data.Transaction): a Beancount transaction
        cfg (Config): Beanclerk config

    Raises:
        ClerkError: if an unexpected action is chosen by the user.

    Returns:
        CategorizationRule | None: a matching rule, or None
    """
    while True:
        if cfg.categorization_rules:
            for rule in cfg.categorization_rules:
                num_matches = 0
                for key, pattern in rule.matches.metadata.items():
                    if (
                        key in transaction.meta
                        and re.search(pattern, transaction.meta[key]) is not None
                    ):
                        num_matches += 1
                if num_matches == len(rule.matches.metadata):
                    return rule

        rich.print("No categorization rule matches the following transaction:")
        rich.print(transaction)
        rich.print("Available actions:")
        rich.print("'r': reload config (you should add a new rule first)")
        rich.print("'i': import as-is (transaction remains unbalanced)")
        match rich.prompt.Prompt.ask("Enter the action", choices=["r", "i"]):
            case "r":
                # Reload only the categorization rules, changing the other
                # parts of the config may cause unexpected issues down
                # the road.
                cfg.categorization_rules = config.load_config(
                    cfg.config_file,
                ).categorization_rules
                continue
            case "i":
                break
            case _ as action:
                raise exceptions.ClerkError(f"Unknown action: {action}")
    return None


def categorize(
    transaction: bean_data.Transaction, cfg: config.Config
) -> bean_data.Transaction:
    """Return transaction categorized according to rules set in config.

    Categorization means adding any missing postings (legs) to a transaction
    to make it balanced. It may also fill in a missing payee, narration or
    transaction flag.

    The rules are applied in the order they are defined in the config file.

    The returned transaction is either a new instance (if new data have
    been added), or the original one if no matching categorization rule was
    found.

    Args:
        transaction (beancount.core.data.Transaction): a Beancount transaction
        cfg (Config): Beanclerk config

    Side effects:
        * `config.categorization_rules` may be modified if the user chooses
        to manually edit and reload the config file during the interactive
        categorization process.

    Returns:
        beancount.core.data.Transaction: a Beancount transaction
    """
    rule = find_categorization_rule(transaction, cfg)
    if rule is None:
        return transaction
    # Do categorize (Transaction is immutable, so we need to create a new one)
    units = transaction.postings[0].units
    postings = copy.deepcopy(transaction.postings)
    postings.append(
        bean_helpers.create_posting(
            account=rule.account,
            units=bean_data.Amount(-units.number, units.currency),
        ),
    )
    return bean_helpers.create_transaction(
        _date=transaction.date,
        flag=rule.flag if rule.flag is not None else transaction.flag,
        payee=rule.payee if rule.payee is not None else transaction.payee,
        narration=rule.narration
        if rule.narration is not None
        else transaction.narration,
        meta=transaction.meta,
        postings=postings,
    )


def append_entry_to_file(entry: bean_data.Directive, filepath: Path) -> None:
    """Append an entry to a file.

    Args:
        entry (beancount.core.data.Directive): a Beancount directive
        filepath (Path): a file path
    """
    with filepath.open("r") as f:
        lines = f.readlines()
        last_line = lines[-1] if lines else ""
    with filepath.open("a") as f:
        if last_line == "\n":
            pass
        elif not last_line.endswith("\n"):
            f.write(2 * "\n")
        else:
            f.write("\n")
        beancount.parser.printer.print_entry(entry, file=f)


def _clr_style(style, msg):
    # https://rich.readthedocs.io/en/stable/style.html#styles
    # https://rich.readthedocs.io/en/stable/appendix/colors.html#appendix-colors
    return f"[{style}]{msg}[/{style}]"


def _clr_br_yellow(msg):
    return _clr_style("bright_yellow", msg)


def _clr_br_green(msg):
    return _clr_style("bright_green", msg)


def _clr_blue(msg):
    return _clr_style("blue", msg)


def _clr_red(msg):
    return _clr_style("red", msg)


def _clr_default(msg):
    # Use 'default' color managed by the terminal
    return _clr_style("default", msg)


def print_import_status(
    new_txns: int,
    importer_balance: bean_data.Amount,
    bean_balance: bean_data.Amount,
) -> None:
    """Print import status to stdout.

    Args:
        new_txns (int): number of imported transactions
        importer_balance (Decimal): balance reported by the importer
        bean_balance (Decimal): balance computed from the Beancount input file
    """
    diff: Decimal = importer_balance.number - bean_balance.number
    if diff == 0:
        balance_status = f"{_clr_br_green('OK:')} {importer_balance}"
    else:
        balance_status = (
            f"{_clr_br_yellow('NOT OK:')} {importer_balance} (diff: {diff})"
        )
    if new_txns == 0:
        txns_status = f"{_clr_default(new_txns)}"
    else:
        txns_status = f"{_clr_blue(new_txns)}"
    rich.print(f"  New transactions: {txns_status}, balance {balance_status}")


def import_transactions(
    config_file: Path,
    from_date: date | None,
    to_date: date | None,
) -> None:
    """For each configured importer, import transactions and print import status.

    Args:
        config_file (Path): path to a config file
        from_date (date | None): the first date to import
        to_date (date | None): the last date to import

    Raises:
        ClerkError: raised if there are errors in the input file
        ClerkError: raised if the initial import date cannot be determined
    """
    cfg = config.load_config(config_file)

    if cfg.insert_pythonpath:
        sys.path.insert(0, str(cfg.input_file.parent))

    entries, errors, _ = beancount.loader.load_file(cfg.input_file)
    if errors != []:
        # TODO: format errors via beancount.parser.printer.format_errors
        raise exceptions.ClerkError(f"Errors in the input file: {errors}")

    for account_cfg in cfg.accounts:
        rich.print(f"Account: '{account_cfg.account}'")
        if from_date is None:
            # TODO: sort entries by date
            last_date = find_last_import_date(entries, account_cfg.account)
            if last_date is None:
                # TODO: catch and add a note the user should use --from-date option
                raise exceptions.ClerkError("Cannot determine the initial import date.")
            from_date = last_date
        if to_date is None:
            # Beancount does not work with times, `date.today()` should be OK.
            to_date = date.today()
        importer: importers.ApiImporterProtocol = config.load_importer(account_cfg)
        try:
            txns, balance = importer.fetch_transactions(
                bean_account=account_cfg.account,
                from_date=from_date,
                to_date=to_date,
            )
        except exceptions.ImporterError as exc:
            rich.print(f"  {_clr_red('Importer Error')}: {exc!s}")
            continue

        new_txns = 0
        for txn in txns:
            if transaction_exists(entries, account_cfg.account, txn.meta["id"]):
                continue
            new_txns += 1
            txn = categorize(txn, cfg)  # noqa: PLW2901
            append_entry_to_file(txn, cfg.input_file)

            # HACK: Update the list of entries without reloading the whole input
            #   file (it may be a quite slow with the Beancount v2). This way
            #   entries become unsorted and potentially unbalanced, but for
            #   a simple balance check it should be OK.
            entries.append(txn)

        print_import_status(
            new_txns,
            balance,
            compute_balance(entries, account_cfg.account, balance.currency),
        )
