"""Tests of the clerk module.

Todo:
    * Some tests are rather incomplete or a mess (mostly sanity only;
    multiple tests, share the same test data). Improve them.
    * Test fn append_entry_to_file.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import rich
from beancount.core.data import Amount, Transaction
from beancount.loader import load_file

from beanclerk.bean_helpers import create_posting, create_transaction
from beanclerk.clerk import (
    categorize,
    compute_balance,
    find_categorization_rule,
    find_last_import_date,
    import_transactions,
    transaction_exists,
)
from beanclerk.config import Config, load_config

CZK = "CZK"


@pytest.fixture()
def entries() -> list[Transaction]:
    """Return a list of Beancount entries."""
    account = "Assets:Dummy"
    postings = [create_posting(account, Amount(Decimal(1), CZK))]
    return [
        create_transaction(
            date(2023, 1, 1),
            meta={"id": "0", "ks": "0558"},
            postings=postings,
        ),
        create_transaction(date(2023, 1, 2), meta={"id": "1"}, postings=postings),
        create_transaction(date(2023, 1, 3), postings=postings),
    ]


def test_find_last_import_date(entries: list[Transaction]) -> None:
    """Test find_last_import_date."""
    account = entries[0].postings[0].account
    assert find_last_import_date([], account) is None
    assert find_last_import_date(entries, account) == date(2023, 1, 2) is not None
    assert find_last_import_date(list(entries[-1]), account) is None
    assert find_last_import_date(entries, "Assets:Nonexistent") is None


def test_transaction_exists(entries: list[Transaction]) -> None:
    """Test transaction_exists."""
    account = entries[0].postings[0].account
    assert not transaction_exists([], account, "0")
    assert transaction_exists(entries, account, "0") is not None
    assert not transaction_exists(entries, account, "-1")


@pytest.fixture()
def config(config_file: Path, ledger: Path) -> Config:
    """Return a Beanclerk Config object."""
    return load_config(config_file)


@pytest.fixture()
def _mock_prompt(monkeypatch) -> None:
    """Mock rich.Prompt.ask."""

    def mock_ask(*args, **kwargs):
        return "i"

    monkeypatch.setattr(rich.prompt.Prompt, "ask", mock_ask)


@pytest.mark.usefixtures("_mock_prompt")
def test_find_categorization_rule(config: Config, entries: list[Transaction]) -> None:
    """Test find_categorization_rule."""
    rule_1 = find_categorization_rule(entries[0], config)
    assert rule_1 is not None
    assert rule_1.account == "Expenses:Todo"
    assert rule_1.payee == "My payee"

    rule_2 = find_categorization_rule(entries[1], config)
    assert rule_2 is None


@pytest.mark.usefixtures("_mock_prompt")
def test_categorize(config: Config, entries: list[Transaction]):
    """Test categorize."""
    txn_1 = categorize(entries[0], config)
    assert txn_1.payee == "My payee"
    assert any("Expenses:Todo" in p.account for p in txn_1.postings)

    txn_2 = categorize(entries[1], config)
    assert txn_2.payee is None
    assert not any("Expenses:Todo" in p.account for p in txn_2.postings)


def test_compute_balance(entries: list[Transaction]):
    """Test compute_balance."""
    account = entries[0].postings[0].account
    assert compute_balance(entries, account, CZK) == Amount(Decimal(3), CZK)
    assert compute_balance(entries, "Assets:Nonexistent", CZK) == Amount(
        Decimal(0),
        CZK,
    )
    with pytest.raises(ValueError, match="not a valid Beancount account"):
        compute_balance(entries, "Invalid", CZK)
    with pytest.raises(ValueError, match="not a valid currency"):
        compute_balance(entries, account, "Invalid")


@pytest.mark.usefixtures("_mock_fio_banka", "_mock_prompt")
def test_import_transactions(config_file: Path, ledger: Path):
    """Test import_transactions."""
    account = "Assets:Banks:Fio:Checking"
    entries, errors, _ = load_file(ledger)
    assert not errors
    assert compute_balance(entries, account, CZK) == Amount(
        Decimal("1000.99"),
        CZK,
    )
    import_transactions(
        config_file,
        from_date=date(2023, 1, 1),
        to_date=date(2023, 1, 1),
    )

    # Don't check for errors, some entries are unbalanced due to
    # _mock_prompt fixture behavior.
    entries, _, _ = load_file(ledger)

    assert compute_balance(entries, account, CZK) == Amount(
        Decimal("2000.10"),
        CZK,
    )
    for txn_id in ("10000000000", "10000000001", "10000000002"):
        assert transaction_exists(entries, account, txn_id)
