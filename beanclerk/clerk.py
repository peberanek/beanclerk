"""Clerk operations.

This module provides operations consumed by the CLI.

Todo:
    * handle exceptions
    * Python docs recommend to use utf-8 encoding for reading and writing files
    * validate txns coming from importers:
        * check that txns have only 1 posting
        * check that txns have id in their metadata
    * Test fn append_entry_to_file.
"""

import copy
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount.core.data import Amount, Directive, Transaction, TxnPosting
from beancount.core.realization import compute_postings_balance, postings_by_account
from beancount.loader import load_file
from beancount.parser.printer import print_entry
from rich import print as rprint
from rich.prompt import Prompt

from .bean_helpers import (
    check_account_name,
    create_posting,
    create_transaction,
    filter_entries,
)
from .config import CategorizationRule, Config, load_config, load_importer
from .exceptions import ClerkError
from .importers import ApiImporterProtocol


def find_last_import_date(entries: list[Directive], account_name: str) -> date | None:
    """Return date of the last imported transaction, or None if not found.

    This function searches for the latest transaction with `id` key in its
    metadata. Entries must be properly ordered.

    Args:
        entries (list[Directive]): a list of Beancount directives
        account_name (str): Beancount account name

    Raises:
        ValueError: if account_name is not a valid Beancount account name

    Returns:
        date | None
    """
    check_account_name(account_name)
    txn_postings = filter_entries(
        postings_by_account(entries)[account_name],
        TxnPosting,
    )
    for txn_posting in reversed(list(txn_postings)):  # latest first
        if txn_posting.txn.meta.get("id") is not None:
            return txn_posting.txn.date
    return None


def transaction_exists(
    entries: list[Directive],
    account_name: str,
    txn_id: str,
) -> bool:
    """Return True if the account has a transaction with the given ID.

    Args:
        entries (list[Directive]): a list of Beancount directives
        account_name (str): Beancount account name
        txn_id (str): transaction ID (`id` key in its metadata)

    Raises:
        ValueError: if account_name is not a valid Beancount account name

    Returns:
        bool
    """
    check_account_name(account_name)
    txn_postings = filter_entries(
        postings_by_account(entries)[account_name],
        TxnPosting,
    )
    return any(txn_posting.txn.meta.get("id") == txn_id for txn_posting in txn_postings)


def compute_balance(
    entries: list[Directive],
    account_name: str,
    currency: str,
) -> Amount:
    """Return account balance for the given account and currency.

    If the account does not exist, it returns Amount 0.

    Args:
        entries (list[Directive]): a list of Beancount directives
        account_name (str): Beancount account name
        currency (str): currency ISO code (e.g. 'USD')

    Raises:
        ValueError: if account_name is not a valid Beancount account name
        ValueError: if currency is not a valid ISO code

    Returns:
        Amount: account balance
    """
    check_account_name(account_name)
    if not re.match(r"^[A-Z]{3}$", currency):
        raise ValueError(f"'{currency}' is not a valid currency code")
    return compute_postings_balance(
        postings_by_account(entries)[account_name],
    ).get_currency_units(currency)


def find_categorization_rule(
    transaction: Transaction,
    config: Config,
) -> CategorizationRule | None:
    """Return a categorization rule matching the given transaction.

    If no rule matches the transaction, the user is prompted to choose
    an action to resolve the situation. The user may also choose not
    to categorize the transaction, None is returned then.

    Args:
        transaction (Transaction): a Beancount transaction
        config (Config): Beanclerk config

    Raises:
        ClerkError: if a categorization rule is invalid.
        ClerkError: if a dangerous pattern is used in a categorization rule.
        ClerkError: if an unexpected action is chosen by the user.

    Returns:
        CategorizationRule | None: a matching rule, or None
    """
    while True:
        if config.categorization_rules:
            for rule in config.categorization_rules:
                if len(rule.matches.metadata) == 0:
                    raise ClerkError(
                        f"Categorization rule: {rule}\n"
                        "Sanity check failed: no patterns to match",
                    )
                num_matches = 0
                for key, pattern in rule.matches.metadata.items():
                    if pattern == "":
                        raise ClerkError(
                            f"Categorization rule: {rule}\n"
                            'Dangerous pattern "" matches everything. '
                            'Use ".*" or "^$" instead.',
                        )
                    if (
                        key in transaction.meta
                        and re.search(pattern, transaction.meta[key]) is not None
                    ):
                        num_matches += 1
                if num_matches == len(rule.matches.metadata):
                    return rule

        rprint("No categorization rule matches the following transaction:")
        rprint(transaction)
        rprint("Available actions:")
        rprint("'r': reload config (you should add a new rule first)")
        rprint("'i': import as-is (transaction remains unbalanced)")
        match Prompt.ask("Enter the action", choices=["r", "i"]):
            case "r":
                # Reload only the categorization rules, changing the other
                # parts of the config may cause unexpected issues down
                # the road.
                config.categorization_rules = load_config(
                    config.config_file,
                ).categorization_rules
                continue
            case "i":
                break
            case _ as action:
                raise ClerkError(f"Unknown action: {action}")
    return None


def categorize(transaction: Transaction, config: Config) -> Transaction:
    """Return transaction categorized according to rules set in config.

    Categorization means adding any missing postings (legs) to a transaction
    to make it balanced. It may also fill in a missing payee, narration or
    transaction flag.

    The rules are applied in the order they are defined in the config file.

    The returned transaction is either a new instance (if new data have
    been added), or the original one if no matching categorization rule was
    found.

    Args:
        transaction (Transaction): a Beancount transaction
        config (Config): Beanclerk config

    Side effects:
        * `config.categorization_rules` may be modified if the user chooses
        to manually edit and reload the config file during the interactive
        categorization process.

    Returns:
        Transaction: a Beancount transaction
    """
    rule = find_categorization_rule(transaction, config)
    if rule is None:
        return transaction
    # Do categorize (Transaction is immutable, so we need to create a new one)
    units = transaction.postings[0].units
    postings = copy.deepcopy(transaction.postings)
    postings.append(
        create_posting(
            account=rule.account,
            units=Amount(-units.number, units.currency),
        ),
    )
    return create_transaction(
        _date=transaction.date,
        flag=rule.flag if rule.flag is not None else transaction.flag,
        payee=rule.payee if rule.payee is not None else transaction.payee,
        narration=rule.narration
        if rule.narration is not None
        else transaction.narration,
        meta=transaction.meta,
        postings=postings,
    )


def append_entry_to_file(entry: Directive, filepath: Path) -> None:
    """Append an entry to a file.

    Args:
        entry (Directive): a Beancount directive
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
        print_entry(entry, file=f)


def print_import_status(
    new_txns: int,
    importer_balance: Decimal,
    bean_balance: Decimal,
) -> None:
    """Print import status to stdout.

    Args:
        new_txns (int): number of imported transactions
        importer_balance (Decimal): balance reported by the importer
        bean_balance (Decimal): balance computed from the Beancount input file
    """
    diff = importer_balance - bean_balance
    if diff == 0:
        balance_status = f"OK: {importer_balance}"
    else:
        balance_status = f"NOT OK: {importer_balance} (diff: {diff})"
    rprint(f"New transactions: {new_txns}, balance {balance_status}")


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
    config = load_config(config_file)
    entries, errors, _ = load_file(config.input_file)
    if errors != []:
        # TODO: format errors via beancount.parser.printer.format_errors
        raise ClerkError(f"Errors in the input file: {errors}")

    for account_config in config.accounts:
        rprint(f"Importing transactions for account: '{account_config.account}'")
        if from_date is None:
            # TODO: sort entries by date
            last_date = find_last_import_date(entries, account_config.account)
            if last_date is None:
                # TODO: catch and add a note the user should use --from-date option
                raise ClerkError("Cannot determine the initial import date.")
            from_date = last_date
        if to_date is None:
            # Beancount does not work with times, `date.today()` should be OK.
            to_date = date.today()  # noqa: DTZ011
        importer: ApiImporterProtocol = load_importer(account_config)
        txns, balance = importer.fetch_transactions(
            bean_account=account_config.account,
            from_date=from_date,
            to_date=to_date,
        )

        new_txns = 0
        for txn in txns:
            if transaction_exists(entries, account_config.account, txn.meta["id"]):
                continue
            new_txns += 1
            txn = categorize(txn, config)  # noqa: PLW2901
            append_entry_to_file(txn, config.input_file)

            # HACK: Update the list of entries without reloading the whole input
            #   file (it may be a quite slow with the Beancount v2). This way
            #   entries become unsorted and potentially unbalanced, but for
            #   a simple balance check it should be OK.
            entries.append(txn)

        print_import_status(
            new_txns,
            balance.number,
            compute_balance(entries, account_config.account, balance.currency).number,
        )
