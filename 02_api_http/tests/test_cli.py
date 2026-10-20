"""测试 CLI 命令 (API + HTTP 方案)."""

from click.testing import CliRunner

from foshan_scraper.__main__ import main


class TestCliHelp:
    """--help 测试."""

    def test_help_exit_code_zero(self) -> None:
        """--help 返回退出码 0."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_help_contains_max_pages(self) -> None:
        """帮助信息包含 --max-pages."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--max-pages" in result.output

    def test_help_contains_output(self) -> None:
        """帮助信息包含 --output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_help_contains_no_detail(self) -> None:
        """帮助信息包含 --no-detail."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--no-detail" in result.output

    def test_help_short_p(self) -> None:
        """帮助信息包含 -p 短选项."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "-p" in result.output

    def test_help_short_o(self) -> None:
        """帮助信息包含 -o 短选项."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "-o" in result.output


class TestCliValidation:
    """参数验证测试 (不访问真实网络)."""

    def test_invalid_max_pages_zero(self) -> None:
        """--max-pages 0 被拒绝,退出码 2."""
        runner = CliRunner()
        result = runner.invoke(main, ["--max-pages", "0"])
        assert result.exit_code == 2

    def test_invalid_max_pages_negative(self) -> None:
        """--max-pages 负数被拒绝,退出码 2."""
        runner = CliRunner()
        result = runner.invoke(main, ["--max-pages", "-1"])
        assert result.exit_code == 2
