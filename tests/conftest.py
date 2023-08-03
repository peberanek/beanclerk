"""Common fixtures and helper functions for tests."""
import os
import shutil
from pathlib import Path

import fio_banka
import pytest

from beanclerk.importers.banka_creditas import ApiImporter

TOP_DIR = Path(os.path.realpath(__file__)).parent


@pytest.fixture()
def _mock_fio_banka(monkeypatch: pytest.MonkeyPatch):
    """Mock fio_banka package."""

    def mock__request(*args, **kwargs) -> str:
        with (TOP_DIR / "importers" / "fio_banka_transactions.json").open("r") as file:
            return file.read()

    monkeypatch.setattr(fio_banka.Account, "_request", mock__request)


@pytest.fixture()
def _mock_creditas_api_importer(monkeypatch: pytest.MonkeyPatch):
    """Mock beanclerk.importers.banka_creditas.ApiImporter.

    creditas pkg does not seem to be easy to mock, mock some of the importer
    methods instead.
    """

    def mock__fetch_transactions(*args, **kwargs) -> bytes:
        with (TOP_DIR / "importers" / "banka_creditas_transactions.xml").open(
            "rb",
        ) as file:
            return file.read()

    monkeypatch.setattr(ApiImporter, "_fetch_transactions", mock__fetch_transactions)


@pytest.fixture()
def config_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return path to the config file."""
    monkeypatch.setenv("TEST_DIR", str(tmp_path))
    return Path(shutil.copy(TOP_DIR / "beanclerk-config.yml", tmp_path))


@pytest.fixture()
def ledger(tmp_path) -> Path:
    """Return path to the ledger file."""
    return Path(shutil.copy(TOP_DIR / "ledger.beancount", tmp_path))
