"""Utilities for Beancount"""
from datetime import date
from pathlib import Path

from beancount.core import realization
from beancount.core.data import (
    EMPTY_SET,
    Account,
    Amount,
    Close,
    Cost,
    CostSpec,
    Flag,
    Meta,
    Posting,
    Transaction,
)
from beancount.core.flags import FLAG_OKAY
from beancount.parser.printer import format_entry

from .utils import ENCODING


def is_closed(real_account: realization.RealAccount) -> bool:
    """Return True if `real_account` is closed; False otherwise."""
    # pylint: disable=isinstance-second-argument-not-valid-type
    return isinstance(
        realization.find_last_active_posting(real_account.txn_postings), Close
    )


def get_real_account(entries, account: str) -> realization.RealAccount:
    """Return RealAccount."""
    real_account = realization.get(realization.realize(entries), account)
    if real_account is None:
        raise ValueError(f"Account '{account}' not found in etries")
    if is_closed(real_account):
        raise ValueError(f"Account '{account}' is closed")
    return real_account


def create_transaction(  # pylint: disable=too-many-arguments
    _date: date,
    flag: Flag = FLAG_OKAY,
    payee: str | None = None,
    narration: str = "",
    tags: frozenset | None = None,
    links: frozenset | None = None,
    postings: list[Posting] | None = None,
    meta: Meta | None = None,
) -> Transaction:
    """Return Transaction."""
    # https://pylint.pycqa.org/en/latest/user_guide/messages/warning/dangerous-default-value.html
    return Transaction(  # type: ignore
        meta=meta if meta is not None else {},
        date=_date,
        flag=flag,
        payee=payee,
        narration=narration,
        tags=tags if tags is not None else EMPTY_SET,
        links=links if links is not None else EMPTY_SET,
        postings=postings if postings is not None else [],
    )


def create_posting(  # pylint: disable=too-many-arguments
    account: Account,
    units: Amount,
    cost: Cost | CostSpec | None = None,
    price: Amount | None = None,
    flag: Flag | None = None,
    meta: Meta | None = None,
) -> Posting:
    """Return Posting."""
    # https://pylint.pycqa.org/en/latest/user_guide/messages/warning/dangerous-default-value.html
    return Posting(
        account=account,
        units=units,
        cost=cost,
        price=price,
        flag=flag,
        meta=meta if meta is not None else {},
    )


def write_entry(entry, filename: Path) -> None:
    """Append an entry to the input file."""
    try:
        with filename.open(encoding=ENCODING) as file:
            contents = file.read()

        if len(contents) == 0:
            raise ValueError(f"File '{filename}' is empty")

        newline: str = "\n"
        with filename.open("a", encoding=ENCODING) as file:
            if contents[-1] != newline:
                file.write(newline)
            file.write(newline)
            file.write(format_entry(entry))

    except FileNotFoundError as exc:
        raise ValueError(f"Cannot read file '{filename}': {exc}") from exc
