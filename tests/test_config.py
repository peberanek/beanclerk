"""Tests of the config module."""
from beanclerk.config import load_config, load_importer
from beanclerk.importers.fio_banka import ApiImporter


def test_load_config(config_file, ledger):
    """Test load_config."""
    load_config(config_file)  # raises on invalid config


def test_load_importer(config_file, ledger):
    """Test load_importer."""
    config = load_config(config_file)
    for account_config in config.accounts:
        importer = load_importer(account_config)  # raises on invalid config
        assert isinstance(importer, ApiImporter)
