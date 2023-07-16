# ruff: noqa: N805

# NOTES:
# * If a validator modifies a value, it should always return a value of the
#   same type: https://github.com/pydantic/pydantic/discussions/3997

import os
from pathlib import Path

import yaml
from beancount.core.account import is_valid
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_settings import BaseSettings

from .exceptions import ConfigError


class AccountConfig(BaseModel):
    name: str
    importer: str  # requires complex validation, moved to the `clerk` module

    # To support custom importers, each importer is set up via extra keys.
    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    def name_is_valid(cls, name: str) -> str:
        if not is_valid(name):
            raise ValueError(f"'{name}' is not a valid Beancount account name")
        return name


# TODO: Does it make sense to prevent additional arbitrary fields?
class Config(BaseSettings):
    input_file: Path
    accounts: list[AccountConfig]

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
            return Config.model_validate(yaml.safe_load(file))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(str(exc)) from exc
