"""API Importer Protocol and utilities for custom importers."""

import abc
from datetime import date
from typing import Any

from beancount.core.data import Amount, Transaction

TransactionReport = tuple[list[Transaction], Amount]


def prepare_meta(d: dict[str, Any]) -> dict[str, str]:
    """Return a dict of metadata for a Beancount transaction.

    Args:
        d (dict[str, Any]): a dict of values

    Returns:
        dict[str, str]: a dict of metadata
    """
    meta = {}
    for k, v in d.items():
        if not (v is None or v == ""):
            meta[k] = str(v)
    return meta


class ApiImporterProtocol(abc.ABC):
    """API Importer Protocol for custom importers.

    All API importers must comply with this interface. Make sure to implement
    all methods decorated with `@abc.abstractmethod`. There are no restrictions
    on other methods, variables or properties.
    """

    @abc.abstractmethod
    def fetch_transactions(
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        """Return a tuple with the list of transactions and the current balance.

        Args:
            bean_account (str): a Beancount account name
            from_date (date): the first date to import
            to_date (date): the last date to import

        Returns:
            TransactionReport: A tuple with the list of transactions and
                the current balance.
        """
