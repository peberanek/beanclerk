from datetime import date

import pytest

import beanclerk.importers.banka_creditas
from beanclerk.importers.banka_creditas import get_transactions

from ..conftest import get_dir


@pytest.fixture()
def _mock__get_transactions(monkeypatch: pytest.MonkeyPatch):
    def mock__get_transactions(*args, **kwargs) -> bytes:
        with (get_dir(__file__) / "banka_creditas_transactions.xml").open("rb") as file:
            return file.read()

    monkeypatch.setattr(
        beanclerk.importers.banka_creditas,
        "_get_transactions",
        mock__get_transactions,
    )


@pytest.mark.usefixtures("_mock__get_transactions")
def test_get_transactions():
    bean_account = "Assets:Account"
    txns, balance = get_transactions(
        token="testkey53mtnzb4hbbnguieebvexzu62q3bvh2imwn9xtyfgzz2z7udwymj38g26",
        account_id="testid0kq95qeeazfnjpfzq89cuytya7tq4awu3r",
        bean_account=bean_account,
        from_date=date(2023, 1, 1),
    )
    print(txns)
    print(balance)
