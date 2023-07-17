"""Tests of the clerk module."""
from datetime import date
from pathlib import Path

from beanclerk.clerk import import_transactions


def test_import_transactions(config_file: Path, ledger: Path) -> None:  # noqa: ARG001
    """Test import_transactions."""
    import_transactions(
        config_file,
        from_date=date(2023, 1, 1),
        to_date=date(2023, 1, 1),
    )