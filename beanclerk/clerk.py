"""Clerk operations"""
import os
from pathlib import Path

import yaml
from voluptuous import All, Coerce, Length, Match, Schema
from voluptuous.error import MultipleInvalid
from voluptuous.validators import PathExists

from .utils import ENCODING


def tweak_config(config: dict) -> dict:
    """Validate config data and convert values to easier-to-use objects."""
    nonempty_str = All(str, Length(min=1))
    schema = Schema(
        {
            "input_file": All(
                Coerce(os.path.expanduser),
                Coerce(os.path.expandvars),
                Coerce(Path),
                PathExists(),  # pylint: disable=no-value-for-parameter
            ),
            "apis": {
                "fio_banka": {
                    "accounts": [
                        {
                            "name": nonempty_str,
                            "token": All(str, Length(min=64, max=64)),
                            # It seems `msg` param does not work: custom msg
                            # doesn't show up in the raised error.
                            "assets": {Match(r"^[A-Z]{3,8}$"): nonempty_str},
                        }
                    ],
                }
            },
        },
        required=True,
    )
    try:
        return schema(config)
    except MultipleInvalid as exc:
        raise ValueError(exc) from exc


def load_config_file(filename: Path) -> dict:
    """Return config from a YAML file as dict."""
    with filename.open("r", encoding=ENCODING) as file:
        return tweak_config(yaml.safe_load(file))
