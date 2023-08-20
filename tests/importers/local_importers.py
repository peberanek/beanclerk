"""Local importers."""
from datetime import date
from decimal import Decimal

from beancount.core.data import Amount

from beanclerk.importers import ApiImporterProtocol, TransactionReport


class LocalImporter(ApiImporterProtocol):
    def fetch_transactions(
        # ruff: noqa: ARG002
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        return ([], Amount(Decimal(0), "CZK"))
