"""测试 CLI 命令."""

from click.testing import CliRunner

from foshan_scraper.__main__ import main


def test_cli_help() -> None:
    """测试 --help 输出."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--url" in result.output
    assert "--pages" in result.output
    assert "--output" in result.output
    assert "--headless" in result.output


def test_cli_invalid_pages() -> None:
    """测试无效页数参数."""
    runner = CliRunner()
    result = runner.invoke(main, ["--pages", "0"])

    assert result.exit_code == 2


def test_cli_default_headless() -> None:
    """测试默认 headless 模式输出."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "headless" in result.output


def test_cli_no_headless_flag_in_help() -> None:
    """测试 --no-headless 在帮助中可见."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--no-headless" in result.output
