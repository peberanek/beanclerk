"""Fio banka, a.s.

docs:
    https://www.fio.cz/bank-services/internetbanking-api
"""

from datetime import date

import fio_banka
from beancount.core.data import Amount, Transaction
from beancount.core.flags import FLAG_WARNING

from ..bean_helpers import create_posting, create_transaction


# This will likely become a part of a class implementing the Importer protocol.
def get_transactions(
    token: str,
    bean_account: str,
    last_date: date | None = None,
) -> tuple[list[Transaction], Amount]:
    """Return a tuple with the list of transactions and the current balance."""
    account = fio_banka.Account(token)
    if last_date is not None:
        account.set_last_date(last_date)
    data = account.last(fio_banka.TransactionsFmt.JSON)

    txns: list[Transaction] = []
    for txn in fio_banka.get_transactions(data):
        meta = {}
        for k, v in txn._asdict().items():  # _asdict() is public method of NamedTuple
            if (
                v is not None
                and v != ""
                and k not in ("date", "amount", "currency")  # will be in Posting
            ):
                meta[k] = str(v)
        txns.append(
            create_transaction(
                _date=txn.date,
                flag=FLAG_WARNING,
                postings=[
                    create_posting(
                        account=bean_account,
                        units=Amount(txn.amount, txn.currency),
                    ),
                ],
                meta=meta,
            ),
        )

    account_info = fio_banka.get_account_info(data)
    return (txns, Amount(account_info.closing_balance, account_info.currency))
