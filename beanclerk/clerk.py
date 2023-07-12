"""Clerk operations

This module servers as a bridge between the importers, the beanclerk command-line
interface and the Beancount.
"""

import copy
import importlib
from datetime import date
from pathlib import Path

import yaml
from beancount.parser import printer

from .exceptions import ConfigError
from .importers import ApiImporterProtocol


def _load_config(filepath: Path) -> dict:
    try:
        with filepath.open("r") as file:
            return yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(str(exc)) from exc


def _get_importer(account_config: dict) -> ApiImporterProtocol:
    module, name = account_config["importer"].rsplit(".", 1)
    # TODO: check cls is a subclass of ApiImporterProtocol; is it possible
    #   to achieve this using Pydantic?
    cls = getattr(importlib.import_module(module), name)
    # HACK: a but ugly, but ATM it seems OK
    cfg = copy.deepcopy(account_config)
    for key in ("name", "bean-account", "importer"):
        cfg.pop(key)
    return cls(**cfg)


def import_transactions(
    configfile: Path,
    from_date: date | None,
    to_date: date | None,
) -> None:
    config = _load_config(configfile)
    for account_config in config["accounts"]:
        if to_date is None:
            to_date = date.today()
        importer: ApiImporterProtocol = _get_importer(account_config)
        txns, balance = importer.fetch_transactions(
            bean_account=account_config["bean-account"],
            from_date=from_date,
            to_date=to_date,
        )
        for txn in txns:
            print(printer.format_entry(txn))
        print()
        print(balance)
