from datetime import date
from decimal import Decimal

import pytest
from beancount.core.data import Amount, Posting, Transaction

from beanclerk.importers.fio_banka import ApiImporter

pytestmark = pytest.mark.usefixtures("_mock_fio_banka")


def test_get_transactions():
    bean_account = "Assets:Account"
    importer = ApiImporter(
        token="testKeyXZVZPOJ4pMrdnPleaUcdUlqy2LqFFVqI4dagXgi1eB1cgLzNjwsWS36bG",
    )
    txns, balance = importer.fetch_transactions(
        bean_account=bean_account,
        from_date=date(2023, 1, 1),
        to_date=date(2023, 1, 1),
    )
    assert balance.number == Decimal("2000.10")
    assert balance.currency == "CZK"
    for txn in txns:
        match txn.meta["id"]:
            case "10000000000":
                assert txn == Transaction(
                    meta={
                        "id": "10000000000",
                        "vs": "1000",
                        "user_identification": "Nákup: example.com, dne 31.12.2022, částka  20.00 USD",  # noqa: E501
                        "remittance_info": "Nákup: example.com, dne 31.12.2022, částka  20.00 USD",  # noqa: E501
                        "type": "Platba kartou",
                        "executor": "Novák, Jan",
                        "comment": "Nákup: example.com, dne 31.12.2022, částka  20.00 USD",  # noqa: E501
                        "order_id": "30000000000",
                    },
                    date=date(2023, 1, 1),
                    flag="*",
                    payee=None,
                    narration="",
                    tags=frozenset(),
                    links=frozenset(),
                    postings=[
                        Posting(
                            account=bean_account,
                            units=Amount(Decimal("2000.0"), "CZK"),
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                    ],
                )
            case "10000000001":
                assert txn == Transaction(
                    meta={
                        "id": "10000000001",
                        "account_id": "9876543210",
                        "bank_id": "0800",
                        "bank_name": "Česká spořitelna, a.s.",
                        "ks": "0558",
                        "vs": "0001",
                        "ss": "0002",
                        "type": "Okamžitá odchozí platba",
                        "executor": "Novák, Jan",
                        "order_id": "30000000001",
                    },
                    date=date(2023, 1, 2),
                    flag="*",
                    payee=None,
                    narration="",
                    tags=frozenset(),
                    links=frozenset(),
                    postings=[
                        Posting(
                            account=bean_account,
                            units=Amount(Decimal("-1500.89"), "CZK"),
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                    ],
                )
            case "10000000002":
                assert txn == Transaction(
                    meta={
                        "id": "10000000002",
                        "account_id": "2345678901",
                        "account_name": "Pavel, Žák",
                        "bank_id": "2010",
                        "bank_name": "Fio banka, a.s.",
                        "type": "Příjem převodem uvnitř banky",
                        "specification": "test specification",
                        "bic": "TESTBICXXXX",
                        "order_id": "30000000002",
                        "payer_reference": "test payer reference",
                    },
                    date=date(2023, 1, 3),
                    flag="*",
                    payee=None,
                    narration="",
                    tags=frozenset(),
                    links=frozenset(),
                    postings=[
                        Posting(
                            account=bean_account,
                            units=Amount(Decimal("500.0"), "CZK"),
                            cost=None,
                            price=None,
                            flag=None,
                            meta={},
                        ),
                    ],
                )
            case _ as _id:
                pytest.fail(f"Unexpected transaction ID: {_id}")
