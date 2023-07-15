"""Clerk operations

This module servers as a bridge between the importers, the beanclerk command-line
interface and the Beancount.
"""

import importlib
from datetime import date
from pathlib import Path

import yaml
from beancount.parser import printer
from pydantic import ValidationError

from .config import AccountConfig, Config
from .exceptions import ConfigError
from .importers import ApiImporterProtocol


# TODO: move into config.py?
def _load_config(filepath: Path) -> Config:
    try:
        with filepath.open("r") as file:
            return Config.model_validate(yaml.safe_load(file))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(str(exc)) from exc


def _get_importer(account_config: AccountConfig) -> ApiImporterProtocol:
    module, name = account_config.importer.rsplit(".", 1)
    try:
        cls = getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as exc:
        raise ConfigError(f"Cannot import '{account_config.importer}'") from exc
    if not issubclass(cls, ApiImporterProtocol):
        raise ConfigError(
            f"'{account_config.importer}' is not a subclass of ApiImporterProtocol",
        )
    try:
        return cls(**account_config.__pydantic_extra__)
    except (TypeError, ValueError) as exc:
        raise ConfigError(str(exc)) from exc


def import_transactions(
    configfile: Path,
    from_date: date | None,
    to_date: date | None,
) -> None:
    for account_config in _load_config(configfile).accounts:
        # FIXME: resolve from_date
        assert from_date is not None, "TBD: from_date is required"  # noqa: S101
        if to_date is None:
            # FIXME: fix Ruff warning
            to_date = date.today()  # noqa: DTZ011
        importer: ApiImporterProtocol = _get_importer(account_config)
        txns, balance = importer.fetch_transactions(
            bean_account=account_config.name,
            from_date=from_date,
            to_date=to_date,
        )
        for txn in txns:
            print(printer.format_entry(txn))  # noqa: T201
        print()  # noqa: T201
        print(balance)  # noqa: T201
