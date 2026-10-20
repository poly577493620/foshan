"""佛山土地交易爬虫 CLI 入口."""

import asyncio
import sys
from pathlib import Path

import click
import structlog

from foshan_scraper.models import LandTransaction
from foshan_scraper.output import export_all
from foshan_scraper.scraper import scrape_land_transactions

log = structlog.get_logger()

# 默认配置
DEFAULT_BASE_URL = "http://jy.ggzy.foshan.gov.cn:3680/TPBank/newweb/framehtml/onlineTradex/index.html"
DEFAULT_MAX_PAGES = 10
DEFAULT_OUTPUT_DIR = Path("./output")


@click.command()
@click.option(
    "--url",
    "-u",
    default=DEFAULT_BASE_URL,
    help="主页 URL",
    show_default=True,
)
@click.option(
    "--pages",
    "-p",
    default=DEFAULT_MAX_PAGES,
    type=int,
    help="爬取页数",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    default=None,
    type=click.Path(path_type=Path),
    help="输出目录 (默认: ./output)",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="无头模式运行浏览器",
    show_default=True,
)
def main(url: str, pages: int, output_dir: Path | None, headless: bool) -> None:
    """佛山土地交易信息爬虫.

    爬取佛山公共资源交易中心的土地交易信息,  # noqa: RUF002
    支持导出 JSON 和 CSV 格式。
    """
    # 验证参数
    if pages < 1:
        click.echo("错误: 页数必须 >= 1", err=True)
        sys.exit(2)

    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    log.info(
        "starting_land_scraper",
        url=url,
        pages=pages,
        output=str(output_dir),
        headless=headless,
    )
    click.echo(f"开始爬取: {url}", err=True)
    click.echo(f"目标页数: {pages}", err=True)
    click.echo(f"浏览器模式: {'无头' if headless else '可视'}", err=True)

    # 收集所有交易记录
    transactions: list[LandTransaction] = []

    try:
        # 异步运行爬虫
        async def run_scraper() -> None:
            async for transaction in scrape_land_transactions(url, max_pages=pages, headless=headless):
                transactions.append(transaction)
                # 实时输出进度
                click.echo(
                    f"[{len(transactions)}] {transaction.land_location or 'N/A'} - {transaction.winner or 'N/A'}",
                    err=True,
                )

        asyncio.run(run_scraper())

    except Exception as e:
        log.error("scraper_failed", error=str(e))
        click.echo(f"爬取失败: {e}", err=True)
        sys.exit(1)

    # 导出数据
    if transactions:
        try:
            json_path, csv_path, excel_path = export_all(transactions, output_dir)
            click.echo("\n导出完成:", err=True)
            click.echo(f"  JSON: {json_path}", err=True)
            click.echo(f"  CSV: {csv_path}", err=True)
            click.echo(f"  Excel: {excel_path}", err=True)
            click.echo(f"  共 {len(transactions)} 条记录", err=True)
        except Exception as e:
            log.error("export_failed", error=str(e))
            click.echo(f"导出失败: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("未获取到任何数据", err=True)


if __name__ == "__main__":
    main()
