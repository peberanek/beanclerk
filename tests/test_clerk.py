"""Tests of the beanclerk.clerk module"""


import pytest
from click import Path

from beanclerk.clerk import load_config_file, tweak_config

from .conftest import EUR, TEST_BOOK


def test_tweak_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, test_book: Path):
    """Test fn tweak_config."""
    config = {
        "input_file": r"~/${TEST_VAR}",
        "apis": {
            "fio_banka": {
                "accounts": [
                    {
                        "name": "my_account_name",
                        "token": "testKeyXZVZPOJ4pMrdnPleaUcdUlqy2LqFFVqI4dagXgi1eB1cgLzNjwsWS36bG",
                        "assets": {EUR: "Assets:BankA:Checking"},
                    }
                ]
            }
        },
    }
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TEST_VAR", TEST_BOOK)
    tweaked_config: dict = tweak_config(config)
    assert tweaked_config["input_file"] == test_book


def test_load_config_file(test_config: Path, test_book: Path):
    """Test fn load_config_file."""
    config = load_config_file(test_config)
    assert config["input_file"] == test_book
