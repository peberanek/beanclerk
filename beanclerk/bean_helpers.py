"""Helpers for Beancount"""
from datetime import date

from beancount.core.data import (
    EMPTY_SET,
    Account,
    Amount,
    Cost,
    CostSpec,
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


def filter_directives(directives, _type):
    """Yield only directives of the given type."""
    for directive in directives:
        if isinstance(directive, _type):
            yield directive
