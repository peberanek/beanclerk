# ruff: noqa: N805

# NOTES:
# * If a validator modifies a value, it should always return a value of the
#   same type: https://github.com/pydantic/pydantic/discussions/3997

import os
from pathlib import Path
from typing import Any

import yaml
from beancount.core.account import is_valid
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigError

# TODO: add note: always return None if a key is missing


class AccountConfig(BaseModel):
    name: str  # TODO: rename to `account`?
    importer: str  # requires complex validation, moved to the `clerk` module

    # To support custom importers, each importer is set up via extra keys.
    # TODO: why explicit allow? To Include extra keys?
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    def name_is_valid(cls, name: str) -> str:
        if not is_valid(name):
            raise ValueError(f"'{name}' is not a valid Beancount account name")
        return name


class MatchCategories(BaseModel):
    metadata: dict[str, str]

    model_config = ConfigDict(extra="forbid")


class ReconcilationRule(BaseModel):
    matches: MatchCategories
    account: str  # TODO: validate
    flag: str | None = None  # TODO: validate
    payee: str | None = None
    narration: str | None = None

    model_config = ConfigDict(extra="forbid")


# TODO: Does it make sense to prevent additional arbitrary fields?
class Config(BaseSettings):
    vars: Any = None  # noqa: A003
    input_file: Path
    accounts: list[AccountConfig]
    reconcilation_rules: list[ReconcilationRule] | None = None

    # additional fields (not present in the config file)
    config_file: Path

    model_config = ConfigDict(extra="forbid")

    @field_validator("input_file")
    def input_file_exists(cls, input_file: Path) -> Path:
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
