"""Tests of the beanclerk.bean_utils module"""
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core.data import Amount, Posting, Transaction
from beancount.core.flags import FLAG_WARNING
from beancount.core.position import Cost
from beancount.core.realization import RealAccount
from beancount.loader import load_file

from beanclerk.bean_utils import (
    create_posting,
    create_transaction,
    get_real_account,
    is_closed,
    write_entry,
)

from .conftest import EUR, TEST_DATE


@pytest.fixture(name="entries")
def _entries(test_book: Path):
    """Provide entries from a test input file."""
    entries, errors, _ = load_file(test_book, log_errors=sys.stderr)
    assert not errors
    return entries


def test_is_closed(entries):
    """Test fn is_closed."""
    real_account = get_real_account(entries, "Assets:BankA:Checking")
    assert not is_closed(real_account)
    with pytest.raises(ValueError, match="is closed"):
        get_real_account(entries, "Assets:BankB:Checking")


def test_get_real_account(entries):
    """Test fn get_real_account."""
    real_account = get_real_account(entries, "Assets:BankA:Checking")
    assert isinstance(real_account, RealAccount)
    with pytest.raises(ValueError, match="not found"):
        get_real_account(entries, "InvalidAccount")
    with pytest.raises(ValueError, match="is closed"):
        get_real_account(entries, "Assets:BankB:Checking")


def test_create_transaction():
    """Test fn create_transaction."""
    payee = "My Payee"
    narration = "My Narration"
    tags = frozenset(["my_tag"])
    links = frozenset(["my_link"])
    meta = {"my_key": "my_val"}
    postings = [
        create_posting("Assets:MyAccount1", Amount(Decimal("1"), EUR)),
        create_posting("Assets:MyAccount2", Amount(Decimal("-1"), EUR)),
    ]
    txn: Transaction = create_transaction(
        _date=TEST_DATE,
        flag=FLAG_WARNING,
        payee=payee,
        narration=narration,
        tags=tags,
        links=links,
        postings=postings,
        meta=meta,
    )
    assert txn.date == TEST_DATE
    assert txn.flag == FLAG_WARNING
    assert txn.payee == payee
    assert txn.narration == narration
    assert txn.tags == tags
    assert txn.links == links
    assert txn.postings == postings
    assert txn.meta == meta


def test_create_posting():
    """Test fn create_posting."""
    account = "Assets:MyAccount"
    amount = Amount(Decimal("1"), EUR)
    cost = Cost(Decimal("1"), EUR, TEST_DATE, "my_label")
    price = amount
    meta = {"my_key": "my_val"}
    posting: Posting = create_posting(
        account=account,
        units=amount,
        cost=cost,
        price=price,
        flag=FLAG_WARNING,
        meta=meta,
    )
    assert posting.account == account
    assert posting.units == amount
    assert posting.cost == cost
    assert posting.price == price
    assert posting.meta == meta


def get_balance(account_name: str, filename: Path) -> Amount:
    """Return account balance as Amount."""
    entries, errors, _ = load_file(filename, log_errors=sys.stderr)
    assert not errors
    real_account = get_real_account(entries, account_name)
    return real_account.balance.get_currency_units(EUR)


def test_write_entry(test_book: Path):  # pylint: disable=unused-argument
    """Test fn append_entry."""
    account = "Assets:BankA:Checking"
    old_balance = get_balance(account, test_book)
    assert old_balance.number is not None

    amount = Decimal("100.00")
    entry = create_transaction(TEST_DATE, narration="Test Transaction")
    entry.postings.extend(
        [
            create_posting(account, Amount(-amount, EUR)),
            create_posting("Expenses:Food", Amount(amount, EUR)),
        ]
    )
    write_entry(entry, test_book)

    new_balance = get_balance(account, test_book)
    assert new_balance.number is not None
    assert new_balance.number == old_balance.number - amount
