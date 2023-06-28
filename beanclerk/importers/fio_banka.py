"""Fio banka, a.s.

docs:
    https://www.fio.cz/bank-services/internetbanking-api
"""

from datetime import date

import fio_banka
from beancount.core.data import Amount, Transaction
from beancount.core.flags import FLAG_WARNING

from ..bean_helpers import create_posting, create_transaction
from . import prepare_meta


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
                meta=prepare_meta(
                    {
                        "transaction_id": txn.transaction_id,
                        "account_id": txn.account,
                        "account_name": txn.account_name,
                        "bank_id": txn.bank_id,
                        "bank_name": txn.bank_name,
                        "ks": txn.ks,
                        "vs": txn.vs,
                        "ss": txn.ss,
                        "user_identification": txn.user_identification,
                        "recipient_message": txn.recipient_message,
                        "type": txn.type,
                        "executor": txn.executor,
                        "specification": txn.specification,
                        "comment": txn.comment,
                        "bic": txn.bic,
                        "order_id": txn.order_id,
                        "payer_reference": txn.payer_reference,
                    },
                ),
            ),
        )

    account_info = fio_banka.get_account_info(data)
    return (txns, Amount(account_info.closing_balance, account_info.currency))
