"""Helpers for Beancount."""
from collections.abc import Generator
from datetime import date
from typing import TypeVar

from beancount.core.account import is_valid
from beancount.core.data import (
    EMPTY_SET,
    Account,
    Amount,
    Cost,
    CostSpec,
    Directive,
    Flag,
    Meta,
    Posting,
    Transaction,
)
from beancount.core.flags import FLAG_OKAY


def create_transaction(
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
    return Transaction(
        meta=meta if meta is not None else {},
        date=_date,
        flag=flag,
        payee=payee,
        narration=narration,
        tags=tags if tags is not None else EMPTY_SET,
        links=links if links is not None else EMPTY_SET,
        postings=postings if postings is not None else [],
    )


def create_posting(
    account: Account,
    units: Amount,
    cost: Cost | CostSpec | None = None,
    price: Amount | None = None,
    flag: Flag | None = None,
    meta: Meta | None = None,
) -> Posting:
    """Return Posting."""
    return Posting(
        account=account,
        units=units,
        cost=cost,
        price=price,
        flag=flag,
        meta=meta if meta is not None else {},
    )


D = TypeVar("D", bound=Directive)


def filter_entries(entries: list[Directive], cls: D) -> Generator[D, None, None]:
    """Yield only instances of a given Beancount directive.

    Args:
        entries (list[Directive]): a list of Beancount directives
        cls (Directive): a Beancount directive class

    Yields:
        Directive: a Beancount directive
    """
    for entry in entries:
        if isinstance(entry, cls):
            yield entry


def check_account_name(name: str) -> None:
    """Check a Beanount account name.

    Args:
        name (str): a Beancount account name

    Raises:
        ValueError: if the account name is invalid
    """
    if not is_valid(name):
        raise ValueError(f"'{name}' is not a valid Beancount account name")
