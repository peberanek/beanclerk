"""Clerk operations

This module servers as a bridge between the importers, the beanclerk command-line
interface and the Beancount.
"""

import copy
import importlib
import re
from datetime import date
from pathlib import Path

from beancount.core.data import Amount, Directive, Transaction, TxnPosting
from beancount.core.realization import compute_postings_balance, postings_by_account
from beancount.loader import load_file
from beancount.parser.printer import format_entry
from rich import print as rprint
from rich.prompt import Prompt

from .bean_helpers import create_posting, create_transaction
from .config import AccountConfig, Config, ReconcilationRule, load_config
from .exceptions import ClerkError, ConfigError
from .importers import ApiImporterProtocol

# TODO: handle exceptions
# TODO: make sure txn has id in its metadata
# TODO: Python docs recommend to use utf-8 encoding for reading and writing files
# TODO: change 'directive' back to 'entry': id does more sense in the context of
#   Beancount V2


def _get_importer(account_config: AccountConfig) -> ApiImporterProtocol:
    module, name = account_config.importer.rsplit(".", 1)
    try:
        cls = getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as exc:
        raise ConfigError(f"Cannot import '{account_config.importer}'") from exc
    if not issubclass(cls, ApiImporterProtocol):
        raise ConfigError(
            f"'{account_config.importer}' is not a subclass of ApiImporterProtocol",
        )
    try:
        return cls(**account_config.model_extra)
    except (TypeError, ValueError) as exc:
        raise ConfigError(str(exc)) from exc


def _get_last_import_date(directives, account_name: str) -> date:
    """Return the date of the last imported Transaction for the given account.

    An imported transaction is a Transaction with the `id` key in its metadata.
    Directives must be properly ordered.

    Raises ClerkError if no Transaction with the `id` key is found.
    """
    txns = []
    posting: TxnPosting | Directive
    # postings_by_account returns postings in the same order as in directives
    # TODO: use bean_helpers.filter_directives
    for posting in postings_by_account(directives)[account_name]:
        if isinstance(posting, TxnPosting):
            txns.append(posting.txn)
    txn: Transaction
    for txn in reversed(txns):
        if txn.meta.get("id") is not None:
            return txn.date
    raise ClerkError(
        "Cannot determine last import date, use --from-date option",
    )


def _txn_id_exists(directives, account_name: str, txn_id: str) -> bool:
    """Return True if the account has a Transaction with the txn_id in its metadata."""
    posting: TxnPosting | Directive
    # postings_by_account returns postings in the same order as in directives
    for posting in postings_by_account(directives)[account_name]:
        if isinstance(posting, TxnPosting) and posting.txn.meta.get("id") == txn_id:
            return True
    return False


def _get_balance(directives, account_name: str, currency: str) -> Amount:
    """Return the balance of the account."""
    return compute_postings_balance(
        postings_by_account(directives)[account_name],
    ).get_currency_units(currency)


def _find_reconcilation_rule(
    txn: Transaction,
    config: Config,
    config_file: Path,
) -> ReconcilationRule | None:
    while True:
        if config.reconcilation_rules:
            for rule in config.reconcilation_rules:
                # TODO: make sure len(rule.matches.metadata) is not 0
                num_matches = 0
                for key, pattern in rule.matches.metadata.items():
                    # FIXME: empty string in pattern always matches
                    if (
                        key in txn.meta
                        and re.search(pattern, txn.meta[key]) is not None
                    ):
                        num_matches += 1
                if num_matches == len(rule.matches.metadata):
                    return rule

        rprint("No rule for the following transaction:")
        rprint(txn)
        rprint("Available actions:")
        rprint("'r': reload config (you should add a new rule first)")
        rprint("'i': import as-is (transaction will be unbalanced)")
        match Prompt.ask("Enter the action", choices=["r", "i"]):
            case "r":
                # Reload only the reconcilation rules, changing the other
                # parts of the config may cause unexpected issues down
                # the road.
                config.reconcilation_rules = load_config(
                    config_file,
                ).reconcilation_rules
                continue
            case "i":
                break
            case _ as action:
                raise ClerkError(f"Unknown action: {action}")
    return None


# FIXME: this fx claims to always return a new Txn
def _reconcile(
    txns: list[Transaction],
    config: Config,
    config_file: Path,
) -> Transaction:
    """Return a new reconciled Transaction.

    Reconcilation means adding a payee, narration and flag (if provided),
    and making the transaction balanced by adding missing postings.

    The rules are applied in the order they are defined in the config file.

    Passing config and config_file is needed for reloading the reconcilation
    rules if the user chooses to do so.

    Side effects:
    * May modify config.reconcilation_rules, if the user chooses to reload them.
    """
    reconciled_txns = []
    for txn in txns:
        rule = _find_reconcilation_rule(txn, config, config_file)
        if rule is None:
            reconciled_txns.append(txn)
        else:
            # Transaction is immutable, so we need to create a new one
            units = txn.postings[0].units
            # TODO: ensure txn has only 1 posting
            postings = copy.deepcopy(txn.postings)
            postings.append(
                create_posting(
                    account=rule.account,
                    units=Amount(-units.number, units.currency),
                ),
            )
            reconciled_txns.append(
                create_transaction(
                    _date=txn.date,
                    flag=rule.flag if rule.flag is not None else txn.flag,
                    payee=rule.payee if rule.payee is not None else txn.payee,
                    narration=rule.narration
                    if rule.narration is not None
                    else txn.narration,
                    meta=txn.meta,
                    postings=postings,
                ),
            )
    return reconciled_txns


def _insert_directives(
    directives: list[Directive],
    filepath: Path,
    lineno: int,
) -> None:
    string = ""
    for d in directives:
        string += format_entry(d) + "\n"
    with filepath.open("r") as f:
        lines = f.readlines()
    lines.insert(lineno - 1, string)  # indices start from 0 (line nums from 1)
    with filepath.open("w") as f:
        f.writelines(lines)


# It does not make sense to reload the input file every time the mark lineno
# is needed. Using a regex is more efficient.
def _get_mark_lineno(filepath: Path, mark_name: str) -> int:
    with filepath.open("r") as f:
        lines = f.readlines()
    mark = re.compile(r'^\d{4}-\d{2}-\d{2} custom "beanclerk-mark" ' + mark_name + "$")
    for i, line in enumerate(lines):
        if mark.match(line):
            return i + 1
    raise ClerkError(f"Beanclerk mark '{mark_name}' not found")


def import_transactions(
    config_file: Path,
    from_date: date | None,
    to_date: date | None,
) -> None:
    config = load_config(config_file)
    for account_config in config.accounts:
        # Inserting new directives into the input file is tricky. If the file
        # is changed between the time we load it and the time we write to it,
        # the line numbers will be wrong.
        #
        # Reloading the input file on each iteration makes sure lineno of each
        # directive is correct. This is necessary for a correct insertion of
        # new directives.
        #
        # There is no check for errors here, because txns from a previous iteration
        # might be imported unbalanced or incomplete if the user chooses so.
        directives, _, _ = load_file(config.input_file)

        if from_date is None:
            from_date = _get_last_import_date(directives, account_config.name)
        if to_date is None:
            # Beancount does not work with times, `date.today()` should be OK.
            to_date = date.today()  # noqa: DTZ011
        importer: ApiImporterProtocol = _get_importer(account_config)
        txns, balance = importer.fetch_transactions(
            bean_account=account_config.name,
            from_date=from_date,
            to_date=to_date,
        )

        new_txns = [
            txn
            for txn in txns
            if not _txn_id_exists(directives, account_config.name, txn.meta["id"])
        ]
<<<<<<< HEAD
        new_txns = _reconcile(new_txns, config, config_file)
        directives, _, _ = load_file(config.input_file)  # FIXME: Inefficient
        _insert_directives(
=======
        new_txns = _reconcile(new_txns, config)
        _insert_directives(  # type: ignore[reportUnusedExpression]
>>>>>>> ca5bf5d (wip: fix lineno)
            new_txns,
            config.input_file,
            _get_mark_lineno(config.input_file, account_config.name),
        )

        # HACK: Update the list of directives without reloading the whole file
        #   (it may be a quite expensive operation with Beancount V2).
        #   Directives become unsorted and potentially unbalanced, but for
        #   a simple balance check it should be OK.
        directives.extend(new_txns)

        # TODO: refactor into a separate function
        diff = (
            balance.number
            - _get_balance(directives, account_config.name, balance.currency).number
        )
        if diff == 0:
            balance_status = f"OK: {balance}"
        else:
            balance_status = f"NOT OK: {balance} (diff: {diff})"
        rprint(f"New transactions: {len(new_txns)}, balance {balance_status}")
