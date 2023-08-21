"""API importer for Banka Creditas a.s.

Todo:
    * handle exceptions

docs:
    https://www.creditas.cz/firma/creditas-api/
    https://github.com/peberanek/creditas
"""

import base64
from datetime import date

import creditas

from . import ApiImporterProtocol, TransactionReport, parse_camt_053_001_02


class ApiImporter(ApiImporterProtocol):
    """API importer for Banka Creditas a.s."""

    def __init__(self, token: str, account_id: str) -> None:
        """Initialize the importer.

        Args:
            token (str): API token (also known as "Bezpečnostní klíč")
            account_id (str): account ID (also known as "Identifikátor účtu")
        """
        self._token = token
        self._account_id = account_id

    def _fetch_transactions(self, from_date: date, to_date: date) -> bytes:
        # Due to complexities of mocking the creditas pkg, this method is not
        # covered by unit tests. When introducing any changes, always make sure
        # it works as expected.
        #
        # Creditas API v1.0.0: Manually generated token can be used only with
        # the following URLs (and the corresponding methods):
        #   /account/current/get
        #   /account/savings/get
        #   /account/balance/get
        #   /account/transaction/search
        #   /account/transaction/export
        #   /account/statement/list
        #   /account/statement/get

        config = creditas.Configuration()
        config.access_token = self._token
        api = creditas.TransactionApi(creditas.ApiClient(config))
        body = creditas.Body8(
            account_id=self._account_id,
            format="XML",
            filter=creditas.AccountTransactionFilter(
                date_from=from_date,
                date_to=to_date,
            ),
        )
        # TODO: handle creditas.rest.ApiException
        data: creditas.InlineResponse20011 = api.d_ps_account_transaction_export_api(
            body=body,
        )
        # TODO: handle other exceptions
        return base64.b64decode(data.export)

    def fetch_transactions(  # noqa: D102
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        return parse_camt_053_001_02(
            self._fetch_transactions(from_date, to_date),
            bean_account,
        )
