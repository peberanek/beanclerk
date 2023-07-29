"""Common fixtures and helper functions for tests."""
import os
import shutil
from pathlib import Path

import fio_banka
import pytest

TOP_DIR = Path(os.path.realpath(__file__)).parent


@pytest.fixture()
def _mock_fio_banka(monkeypatch: pytest.MonkeyPatch):
    """Mock fio_banka package."""

    def mock__request(*args, **kwargs) -> str:
        with (TOP_DIR / "importers" / "fio_banka_transactions.json").open("r") as file:
            return file.read()

    monkeypatch.setattr(fio_banka.Account, "_request", mock__request)


@pytest.fixture()
def config_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return path to the config file."""
    monkeypatch.setenv("TEST_DIR", str(tmp_path))
    return Path(shutil.copy(TOP_DIR / "beanclerk-config.yml", tmp_path))


@pytest.fixture()
def ledger(tmp_path) -> Path:
    """Return path to the ledger file."""
    return Path(shutil.copy(TOP_DIR / "ledger.beancount", tmp_path))
