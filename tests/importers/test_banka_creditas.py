from datetime import date
from decimal import Decimal

import pytest
from beancount.core.data import Amount, Posting, Transaction

from beanclerk.importers.banka_creditas import ApiImporter

pytestmark = pytest.mark.usefixtures("_mock_creditas_api_importer")


class TestApiImporter:
    """Test ApiImporter."""

    IMPORTER = ApiImporter(
        token="testKeyXZVZPOJ4pMrdnPleaUcdUlqy2LqFFVqI4dagXgi1eB1cgLzNjwsWS36bG",
        account_id="testId0kq95qeeazfnjpfzq89cuytya7tq4awu3r",
    )

    def test_get_transactions(self):
        """Test get_transactions."""
        bean_account = "Assets:Account"
        txns, balance = self.IMPORTER.fetch_transactions(
            bean_account=bean_account,
            from_date=date(2023, 1, 1),
            to_date=date(2023, 1, 1),
        )
        assert balance.number == Decimal("1000.10")
        assert balance.currency == "CZK"
        assert len(txns) == 1
        assert txns[0] == Transaction(
            meta={
                "id": "RLZ-1000000000",
                "account_id": "1234567890",
                "bank_id": "0800",
                "ks": "2",
                "vs": "0",
                "ss": "1",
                "remittance_info": "Zprava pro prijemce",
                "executor": "Zak, Pavel",
            },
            date=date(2023, 1, 1),
            flag="*",
            payee=None,
            narration="",
            tags=frozenset(),
            links=frozenset(),
            postings=[
                Posting(
                    account="Assets:Account",
                    units=Amount(Decimal("100.99"), "CZK"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta={},
                ),
            ],
        )
