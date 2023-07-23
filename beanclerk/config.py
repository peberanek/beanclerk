"""Configuration file parsing and validation.

Notes:
    * If a validator modifies a value, it should always return the same type:
    https://github.com/pydantic/pydantic/discussions/3997

TODO:
    * Add missing field validators.
"""
# ruff: noqa: N805

import os
from pathlib import Path
from typing import Any

import yaml
from beancount.core.account import is_valid
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigError


class BaseModelStrict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountConfig(BaseModel):
    """Account config model

    Allows extra fields to support custom configuration of importers.
    """

    name: str
    importer: str

    model_config = ConfigDict(extra="allow")  # allows access to extra fields

    @field_validator("name")
    def name_is_valid(cls, name: str) -> str:
        if not is_valid(name):
            raise ValueError(f"'{name}' is not a valid Beancount account name")
        return name


class MatchCategories(BaseModelStrict):
    metadata: dict[str, str]


class ReconcilationRule(BaseModelStrict):
    matches: MatchCategories
    account: str
    flag: str | None = None
    payee: str | None = None
    narration: str | None = None


class Config(BaseSettings):
    """Beanclerk configuration

    Most attributes are defined in a config file. Config is a Pydantic
    model, and raises a `pydantic.ValidationError` on invalid fields.
    """

    vars: Any = None  # noqa: A003
    input_file: Path
    accounts: list[AccountConfig]
    reconcilation_rules: list[ReconcilationRule] | None = None

    # fields not present in the config file
    config_file: Path

    model_config = ConfigDict(extra="forbid")

    @field_validator("input_file")
    def input_file_exists(cls, input_file: Path) -> Path:
        # Side effects:
        #   * expands user (`~`) and environment variables
        filename: str = os.path.expandvars(input_file.expanduser())
        if not os.path.isabs(filename):  # noqa: PTH117
            filename = os.path.normpath(Path.cwd() / filename)
        input_file = Path(filename)
        if not input_file.exists():
            raise ValueError(f"Input file '{input_file}' does not exist")
        return input_file


def load_config(filepath: Path) -> Config:
    try:
        with filepath.open("r") as file:
            contents = yaml.safe_load(file)
            contents["config_file"] = filepath
            return Config.model_validate(contents)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(str(exc)) from exc
