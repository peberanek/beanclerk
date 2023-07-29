"""Beanclerk command-line interface."""

from datetime import date
from pathlib import Path

import click

from .clerk import import_transactions
from .exceptions import BeanclerkError

CONFIG_FILE = "beanclerk-config.yml"


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=False,
)
@click.version_option()
@click.option(
    "-c",
    "--config-file",
    default=Path.cwd() / CONFIG_FILE,
    type=click.Path(path_type=Path),
    help=f"Path to a config file; defaults to `{CONFIG_FILE}` in the current working directory.",  # noqa: E501
)
@click.pass_context
def cli(ctx: click.Context, config_file: Path) -> None:
    """Automation for Beancount.

    Import and categorize transactions via API importers and user-defined rules.
    """
    # https://click.palletsprojects.com/en/8.1.x/commands/#nested-handling-and-contexts
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file


_ISO_DATE_FMT: str = "YYYY-MM-DD"


class Date(click.ParamType):
    """A convenience date type for Click.

    Converts dates to a date (instead of datetime).
    """

    name = "date"

    def convert(self, value, param, ctx):  # noqa: D102
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value)
        except ValueError:
            self.fail(
                f"'{value}' is not a valid date format ({_ISO_DATE_FMT})",
                param,
                ctx,
            )


@cli.command("import")
@click.option(
    "--from-date",
    type=Date(),
    help=f"The first date to import ({_ISO_DATE_FMT}).",
)
@click.option(
    "--to-date",
    type=Date(),
    help=f"The last date to import ({_ISO_DATE_FMT}).",
)
@click.pass_context
def import_(ctx: click.Context, from_date: Date, to_date: Date) -> None:
    """Import transactions and check the current balance."""
    try:
        import_transactions(
            config_file=ctx.obj["config_file"],
            from_date=from_date,
            to_date=to_date,
        )
    except BeanclerkError as exc:
        raise click.ClickException(str(exc)) from exc
