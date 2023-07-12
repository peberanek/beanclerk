"""API importer protocol and utilities for custom importers"""

import abc
from datetime import date

from beancount.core.data import Amount, Transaction

TransactionReport = tuple[list[Transaction], Amount]


def prepare_meta(d: dict) -> dict:
    """Return a dict of metadata for a transaction."""
    new_dict = {}
    for k, v in d.items():
        if not (v is None or v == ""):
            new_dict[k] = str(v)
    return new_dict


class ApiImporterProtocol(abc.ABC):
    @abc.abstractmethod
    def fetch_transactions(
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        """Return a tuple with the list of transactions and the current balance.

        Args:
            bean_account: Beancount account name.
            from_date: Date from which to fetch transactions.
            to_date: Date to which to fetch transactions.

        Returns:
            tuple: A tuple with the list of transactions and the current balance.
        """
