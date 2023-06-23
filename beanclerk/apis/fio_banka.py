"""Fio banka, a.s.

docs:
    https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf
    https://www.fio.cz/bank-services/internetbanking-api
    https://www.fio.cz/xsd/IBSchema.xsd
"""
from datetime import date
from decimal import Decimal

from beancount.core.data import Amount, Transaction

from ..bean_utils import create_posting, create_transaction


# FIXME: Return real data
def account_statement() -> tuple[Amount, list[Transaction]]:
    txns = [
        create_transaction(
            _date=date(2023, 1, 1),
            narration="Test transaction",
            meta={
                "transaction_id": "0",
            },
            postings=[
                create_posting(
                    account="Assets:BankA:Checking",
                    units=Amount(Decimal("-100"), "EUR"),
                ),
                create_posting(
                    account="Expenses:Food", units=Amount(Decimal("100"), "EUR")
                ),
            ],
        )
    ]
    return (Amount(Decimal("1000.00"), "EUR"), txns)
