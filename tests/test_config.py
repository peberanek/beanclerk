"""Tests of the config module."""
from pathlib import Path

import pydantic
import pytest

from beanclerk.config import Config, load_config, load_importer
from beanclerk.importers import ApiImporterProtocol

_valid_accounts = [
    {
        "account": "Assets:Bank:Checking",
        "importer": "beanclerk.importers.fio_banka.ApiImporter",
        "token": "testKeyFVqI4dagXgi1eB1cgLzNjwsWS36bGXZVZPOJ4pMrdnPleaUcdUlqy2LqF",
    },
]
_valid_categorization_rules = [
    {
        "matches": {
            "metadata": {"key": "pattern"},
        },
        "account": "Expenses:Dummy",
    },
]


@pytest.mark.parametrize(
    ("invalid_config", "exception_msg"),
    [
        (
            {
                "input_file": "nonexistent",
                "accounts": _valid_accounts,
                "categorization_rules": _valid_categorization_rules,
            },
            r"Input file .*/nonexistent.* does not exist",
        ),
        (
            {
                "accounts": _valid_accounts,
                "categorization_rules": [
                    {
                        "matches": {
                            "metadata": {},
                        },
                        "account": "Expenses:Dummy",
                    },
                ],
            },
            "No patterns in metadata",
        ),
        (
            {
                "accounts": _valid_accounts,
                "categorization_rules": [
                    {
                        "matches": {
                            "metadata": {"key": ""},
                        },
                        "account": "Expenses:Dummy",
                    },
                ],
            },
            "Dangerous pattern: empty string",
        ),
        (
            {
                "accounts": _valid_accounts,
                "categorization_rules": [
                    {
                        "matches": {
                            "metadata": {"key": "|foo"},
                        },
                        "account": "Expenses:Dummy",
                    },
                ],
            },
            "Dangerous pattern: regex '|...'",
        ),
    ],
    ids=[
        "nonexistent-input-file",
        "no-metadata",
        "dangerous-pattern-empty-str",
        "dangerous-pattern-regex-matches-everything",
    ],
)
def test_validation(
    config_file: Path,
    ledger: Path,
    invalid_config: dict,
    exception_msg: str,
) -> None:
    if "input_file" not in invalid_config:
        invalid_config["input_file"] = str(ledger)
    if "config_file" not in invalid_config:
        invalid_config["config_file"] = str(config_file)
    with pytest.raises(pydantic.ValidationError, match=exception_msg):
        Config(**invalid_config)


def test_load_config(config_file, ledger):
    """Test load_config."""
    load_config(config_file)  # raises on invalid config


def test_load_importer(config_file, ledger):
    """Test load_importer."""
    config = load_config(config_file)
    for account_config in config.accounts:
        importer = load_importer(account_config)  # raises on invalid config
        assert isinstance(importer, ApiImporterProtocol)
