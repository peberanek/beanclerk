"""Helpers for Beancount."""
from collections.abc import Generator
from datetime import date
from typing import TypeVar

import beancount.core.account as bean_account
import beancount.core.data as bean_data
import beancount.core.flags as bean_flags


def create_transaction(
    _date: date,
    flag: bean_data.Flag = bean_flags.FLAG_OKAY,
    payee: str | None = None,
    narration: str = "",
    tags: frozenset | None = None,
    links: frozenset | None = None,
    postings: list[bean_data.Posting] | None = None,
    meta: bean_data.Meta | None = None,
) -> bean_data.Transaction:
    """Return Transaction."""
    return bean_data.Transaction(
        meta=meta if meta is not None else {},
        date=_date,
        flag=flag,
        payee=payee,
        narration=narration,
        tags=tags if tags is not None else bean_data.EMPTY_SET,
        links=links if links is not None else bean_data.EMPTY_SET,
        postings=postings if postings is not None else [],
    )


def create_posting(
    account: bean_data.Account,
    units: bean_data.Amount,
    cost: bean_data.Cost | bean_data.CostSpec | None = None,
    price: bean_data.Amount | None = None,
    flag: bean_data.Flag | None = None,
    meta: bean_data.Meta | None = None,
) -> bean_data.Posting:
    """Return Posting."""
    return bean_data.Posting(
        account=account,
        units=units,
        cost=cost,
        price=price,
        flag=flag,
        meta=meta if meta is not None else {},
    )


D = TypeVar("D", bound=bean_data.Directive)


def filter_entries(
    entries: list[bean_data.Directive], cls: D
) -> Generator[D, None, None]:
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


def validate_account_name(name: str) -> None:
    """Validate a Beanount account name.

    Args:
        name (str): a Beancount account name
    """
    if not bean_account.is_valid(name):
        raise ValueError(f"'{name}' is not a valid Beancount account name")
