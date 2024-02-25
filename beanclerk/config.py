"""Configuration file parsing and validation.

Notes:
    * If a validator modifies a value, it should always return the same type:
    https://github.com/pydantic/pydantic/discussions/3997

Todo:
    * Add missing field validators.
        * Validate importer path.
"""
# Disabling due to Pydantic notation (`cls` instead of `self`).
# ruff: noqa: N805

import importlib
import os
from pathlib import Path
from typing import Any

import pydantic
import pydantic_settings
import yaml

from . import bean_helpers, exceptions, importers


class _BaseModelStrict(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")


class AccountConfig(pydantic.BaseModel):
    """Account config model.

    Allows extra fields to support custom configuration of importers.
    """

    account: str
    importer: str

    model_config = pydantic.ConfigDict(extra="allow")  # allows access to extra fields

    @pydantic.field_validator("account")
    def name_is_valid(cls, name: str) -> str:
        """Validate account name."""
        bean_helpers.validate_account_name(name)
        return name


class MatchCategories(_BaseModelStrict):
    """Match categories model."""

    metadata: dict[str, str]

    @pydantic.field_validator("metadata")
    def metadata_is_valid(cls, metadata: dict[str, str]) -> dict[str, str]:
        """Validate metadata."""
        if not metadata:
            raise ValueError("No patterns in metadata")
        for pattern in metadata.values():
            if pattern == "":
                raise ValueError("Dangerous pattern: empty string matches everything")
            if pattern.startswith("|"):
                raise ValueError("Dangerous pattern: regex '|...' matches everything")
        return metadata


class CategorizationRule(_BaseModelStrict):
    """Categorization rule model."""

    matches: MatchCategories
    account: str
    flag: str | None = None
    payee: str | None = None
    narration: str | None = None


class Config(pydantic_settings.BaseSettings):
    """Beanclerk config model.

    Most attributes are defined in a config file. Config is a Pydantic
    model, and raises a `pydantic.ValidationError` on invalid fields.
    """

    vars: Any = None
    input_file: Path
    insert_pythonpath: bool = False
    accounts: list[AccountConfig]
    categorization_rules: list[CategorizationRule] | None = None

    # fields not present in the config file
    config_file: Path

    model_config = pydantic_settings.SettingsConfigDict(
        extra="forbid",
        env_file=".beanclerk_env",
        env_prefix="beanclerk_",  # case-insensitive
    )

    @pydantic.field_validator("input_file")
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

    @classmethod
    def settings_customise_sources(  # noqa: D102
        cls,
        settings_cls: type[pydantic_settings.BaseSettings],  # noqa: ARG003
        init_settings: pydantic_settings.PydanticBaseSettingsSource,
        env_settings: pydantic_settings.PydanticBaseSettingsSource,
        dotenv_settings: pydantic_settings.PydanticBaseSettingsSource,
        file_secret_settings: pydantic_settings.PydanticBaseSettingsSource,
    ) -> tuple[pydantic_settings.PydanticBaseSettingsSource, ...]:
        # Change the default order of priority:
        # https://docs.pydantic.dev/latest/usage/pydantic_settings/#customise-settings-sources
        return (env_settings, dotenv_settings, init_settings, file_secret_settings)


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
    except (OSError, yaml.YAMLError, pydantic.ValidationError) as exc:
        raise exceptions.ConfigError(str(exc)) from exc


def load_importer(account_config: AccountConfig) -> importers.ApiImporterProtocol:
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
        raise exceptions.ConfigError(
            f"Cannot import '{account_config.importer}': {exc!s}",
        ) from exc
    if not issubclass(cls, importers.ApiImporterProtocol):
        raise exceptions.ConfigError(
            f"'{account_config.importer}' is not a subclass of ApiImporterProtocol",
        )
    try:
        return cls(**account_config.model_extra)
    except (TypeError, ValueError) as exc:
        raise exceptions.ConfigError(
            f"Cannot instantiate '{account_config.importer}': {exc!s}",
        ) from exc
