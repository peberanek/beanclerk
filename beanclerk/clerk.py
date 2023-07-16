"""Clerk operations

This module servers as a bridge between the importers, the beanclerk command-line
interface and the Beancount.
"""

import importlib
from datetime import date
from pathlib import Path

from beancount.core.data import Directive, Transaction, TxnPosting
from beancount.core.realization import postings_by_account
from beancount.loader import load_file
from beancount.parser import printer

from .config import AccountConfig, load_config
from .exceptions import ClerkError, ConfigError
from .importers import ApiImporterProtocol

# TODO: handle exceptions


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
        return cls(**account_config.__pydantic_extra__)
    except (TypeError, ValueError) as exc:
        raise ConfigError(str(exc)) from exc


def _get_last_import_date(directives, account_name: str) -> date | None:
    """Return the date of the last imported Transaction for the given account.

    An imported transaction is a Transaction with the `id` key in its metadata.
    Directives must be properly ordered.
    """
    txns = []
    posting: TxnPosting | Directive
    # postings_by_account returns postings in the same order as in directives
    for posting in postings_by_account(directives)[account_name]:
        if isinstance(posting, TxnPosting):
            txns.append(posting.txn)
    txn: Transaction
    for txn in reversed(txns):
        if txn.meta.get("id") is not None:
            return txn.date
    return None


def _txn_id_exists(directives, account_name: str, txn_id: str) -> bool:
    """Return True if the account has a Transaction with the txn_id in its metadata."""
    posting: TxnPosting | Directive
    # postings_by_account returns postings in the same order as in directives
    for posting in postings_by_account(directives)[account_name]:
        if isinstance(posting, TxnPosting) and posting.txn.meta.get("id") == txn_id:
            return True
    return False


def import_transactions(
    config_file: Path,
    from_date: date | None,
    to_date: date | None,
) -> None:
    config = load_config(config_file)
    directives, errors, _ = load_file(config.input_file)
    if errors != []:
        raise ClerkError(f"Errors in the Beancount input file: {errors}")
    for account_config in config.accounts:
        if from_date is None:
            last_date = _get_last_import_date(directives, account_config.name)
            if last_date is None:
                raise ClerkError(
                    "Cannot determine last import date, use --from-date option",
                )
            from_date = last_date
        if to_date is None:
            # As Beancount does not work with times, I belive simple
            # `date.today()` is OK.
            to_date = date.today()  # noqa: DTZ011
        importer: ApiImporterProtocol = _get_importer(account_config)
        txns, balance = importer.fetch_transactions(
            bean_account=account_config.name,
            from_date=from_date,
            to_date=to_date,
        )
        for txn in txns:
            if _txn_id_exists(directives, account_config.name, txn.meta["id"]):
                continue

            # Reconcile

            # Write to the input file
            print(printer.format_entry(txn))  # noqa: T201
        print()  # noqa: T201
        print(balance)  # noqa: T201
