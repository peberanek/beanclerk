"""API importer for Fio banka, a.s.

docs:
    https://www.fio.cz/bank-services/internetbanking-api
    https://github.com/peberanek/fio-banka
"""

from datetime import date

import fio_banka
from beancount.core.data import Amount, Transaction

from ..bean_helpers import create_posting, create_transaction
from ..exceptions import ImporterError
from . import ApiImporterProtocol, TransactionReport, refine_meta


class ApiImporter(ApiImporterProtocol):
    """API importer for Fio banka, a.s."""

    def __init__(self, token: str) -> None:
        """Initialize the importer.

        Args:
            token (str): API token
        """
        self._token = token

    def fetch_transactions(  # noqa: D102
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        try:
            client = fio_banka.Account(self._token)
            statement = client.periods(
                from_date, to_date, fio_banka.TransactionsFmt.JSON
            )
        except (ValueError, fio_banka.FioBankaError) as exc:
            raise ImporterError(str(exc)) from exc

        txns: list[Transaction] = []
        for txn in fio_banka.get_transactions(statement):
            txns.append(
                create_transaction(
                    _date=txn.date,
                    postings=[
                        create_posting(
                            account=bean_account,
                            units=Amount(txn.amount, txn.currency),
                        ),
                    ],
                    meta=refine_meta(
                        {
                            "id": txn.transaction_id,
                            "account_id": txn.account_id,
                            "account_name": txn.account_name,
                            "bank_id": txn.bank_id,
                            "bank_name": txn.bank_name,
                            "ks": txn.ks,
                            "vs": txn.vs,
                            "ss": txn.ss,
                            "user_identification": txn.user_identification,
                            "remittance_info": txn.remittance_info,
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

        account_info = fio_banka.get_account_info(statement)
        return (txns, Amount(account_info.closing_balance, account_info.currency))
