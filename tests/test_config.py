"""Tests of the config module."""
from beanclerk.config import load_config


def test_load_config(config_file, ledger):  # noqa: ARG001
    """Test load_config."""
    load_config(config_file)  # raises an exception if the config is invalid
