"""Test of the beanclerk command-line interface"""
from pathlib import Path

import pytest
from click.testing import CliRunner

from beanclerk.cli import cli


@pytest.fixture(name="runner")
def _runner() -> CliRunner:
    """Set up and provide CliRunner for running CLI."""
    return CliRunner(mix_stderr=False)


def assert_is_help_msg(msg: str) -> None:
    """Assert `msg` is a Click-formated help message."""
    for word in ("Usage", "Options", "Commands"):
        assert word in msg


def test_no_args(runner: CliRunner):
    """Test invoking CLI without any args.

    By default, Click does not return error if CLI is invoked without
    args, even if it does not anything useful.

    Expects:
        * Exit status 1
        * Help msg is printed into stderr.
    """
    result = runner.invoke(cli, "")
    assert result.exit_code == 1
    assert_is_help_msg(result.stderr)


def test_short_help_arg(runner: CliRunner):
    """Test invoking CLI with custom `-h` arg.

    Click does not provide `-h` arg by default.

    Expects:
        * Exit status 0
        * Help msg is printed into stdout.
    """
    result = runner.invoke(cli, "-h")
    assert result.exit_code == 0
    assert_is_help_msg(result.stdout)


class TestCmdImport:
    """Tests of the command 'import'"""

    @staticmethod
    def test_no_args(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        runner: CliRunner,
        test_config: Path,
        test_book: Path,
    ):  # pylint: disable=unused-argument
        """Test invoking cmd without any args."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, "import")
        assert result.exit_code == 0
        print(result.stdout)
