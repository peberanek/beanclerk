"""Configuration file parsing and validation.

Notes:
    * If a validator modifies a value, it should always return the same type:
    https://github.com/pydantic/pydantic/discussions/3997

Todo:
    * Add missing field validators.
"""
# Disabling due to Pydantic notation (`cls` instead of `self`).
# ruff: noqa: N805

import importlib
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_settings import BaseSettings

from .bean_helpers import check_account_name
from .exceptions import ConfigError
from .importers import ApiImporterProtocol


class _BaseModelStrict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountConfig(BaseModel):
    """Account config model.

    Allows extra fields to support custom configuration of importers.
    """

    account: str
    importer: str

    model_config = ConfigDict(extra="allow")  # allows access to extra fields

    @field_validator("account")
    def name_is_valid(cls, name: str) -> str:
        """Validate account name."""
        check_account_name(name)
        return name


class MatchCategories(_BaseModelStrict):
    """Match categories model."""

    metadata: dict[str, str]


class CategorizationRule(_BaseModelStrict):
    """Categorization rule model."""

    matches: MatchCategories
    account: str
    flag: str | None = None
    payee: str | None = None
    narration: str | None = None


class Config(BaseSettings):
    """Beanclerk config model.

    Most attributes are defined in a config file. Config is a Pydantic
    model, and raises a `pydantic.ValidationError` on invalid fields.
    """

    vars: Any = None  # noqa: A003
    input_file: Path
    accounts: list[AccountConfig]
    categorization_rules: list[CategorizationRule] | None = None

    # fields not present in the config file
    config_file: Path

    model_config = ConfigDict(extra="forbid")

    @field_validator("input_file")
    def input_file_exists(cls, input_file: Path) -> Path:
        """Validate input file exists.

        Side effects:
            * expands user (`~`) and environment variables
        """
        filename: str = os.path.expandvars(input_file.expanduser())
        if not os.path.isabs(filename):  # noqa: PTH117
            filename = os.path.normpath(Path.cwd() / filename)
        input_file = Path(filename)
        if not input_file.exists():
            raise ValueError(f"Input file '{input_file}' does not exist")
        return input_file


def load_config(filepath: Path) -> Config:
    """Load and validate and a Beanclerk config file object.

    Args:
        filepath (Path): path to a config file

    Raises:
        ConfigError: Raised when the config file cannot be loaded or is invalid

    Returns:
        Config: a validated config object
    """
    try:
        with filepath.open("r") as file:
            contents = yaml.safe_load(file)
            contents["config_file"] = filepath
            return Config.model_validate(contents)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(str(exc)) from exc


def load_importer(account_config: AccountConfig) -> ApiImporterProtocol:
    """Return an instance of importer defined in the account config.

    Args:
        account_config (AccountConfig): an account configuration

    Raises:
        ConfigError: Raised when the importer cannot be loaded

    Returns:
        ApiImporterProtocol: an instance of a particular importer implementing
            the API Importer Protocol
    """
    module, name = account_config.importer.rsplit(".", 1)
    try:
        cls = getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as exc:
        raise ConfigError(
            f"Cannot import '{account_config.importer}': {exc!s}",
        ) from exc
    if not issubclass(cls, ApiImporterProtocol):
        raise ConfigError(
            f"'{account_config.importer}' is not a subclass of ApiImporterProtocol",
        )
    try:
        return cls(**account_config.model_extra)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"Cannot instantiate '{account_config.importer}': {exc!s}",
        ) from exc
