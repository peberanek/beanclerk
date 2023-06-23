"""The command-line interface for Beanclerk"""

from pathlib import Path

import click

from .apis.fio_banka import account_statement
from .bean_utils import write_entry
from .clerk import load_config_file

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
CONFIG_FILE: str = "bean-clerk.yaml"


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx):
    """Automate repetitive tasks when managing Beancount files."""
    if ctx.invoked_subcommand is None:
        click.echo(cli.get_help(ctx), err=True)
        raise click.exceptions.Exit(1)


@cli.command("import")
def _import():
    """Import transactions and check resulting balance."""
    # Setting config_file at module level does not change working dir in tests.
    config_file: Path = Path.cwd() / CONFIG_FILE

    # get data from API
    balance, txns = account_statement()
    # write data
    for txn in txns:
        write_entry(txn, load_config_file(config_file)["input_file"])
    # print num txns, balance
    print("num txns:", len(txns), "balance:", balance)
