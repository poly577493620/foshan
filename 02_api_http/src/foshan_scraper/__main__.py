"""佛山土地交易爬虫 CLI 入口."""

import asyncio
import sys
from pathlib import Path

import click
import structlog

from foshan_scraper.api_fetcher import fetch_all
from foshan_scraper.detail_fetcher import enrich_with_details
from foshan_scraper.models import LandTransaction
from foshan_scraper.output import export_all

log = structlog.get_logger()

DEFAULT_MAX_PAGES = 10
DEFAULT_OUTPUT_DIR = Path("./output")


def _print_header(max_pages: int, output_dir: Path, no_detail: bool) -> None:
    """打印运行参数头部."""
    divider = "━" * 50
    click.echo(divider, err=True)
    click.echo("  佛山土地交易信息爬虫 (API + HTTP 方案)", err=True)
    click.echo(divider, err=True)
    click.echo(f"  最大页数 : {max_pages}", err=True)
    click.echo(f"  输出目录 : {output_dir}", err=True)
    click.echo(f"  详情页   : {'跳过' if no_detail else '抓取'}", err=True)
    click.echo(divider, err=True)


def _print_list_fetch_progress(count: int) -> None:
    """打印列表获取进度 (每 10 条或首条)."""
    if count % 10 == 0 or count == 1:
        click.echo(f"  已获取 {count} 条记录...", err=True)


def _print_result(
    json_path: Path,
    csv_path: Path,
    excel_path: Path,
    total: int,
) -> None:
    """打印导出结果."""
    divider = "━" * 50
    click.echo(divider, err=True)
    click.echo("  导出完成!", err=True)
    click.echo(f"  JSON : {json_path}", err=True)
    click.echo(f"  CSV  : {csv_path}", err=True)
    click.echo(f"  Excel: {excel_path}", err=True)
    click.echo(f"  共 {total} 条记录", err=True)
    click.echo(divider, err=True)


async def _fetch_and_enrich(
    max_pages: int,
    no_detail: bool,
) -> list[LandTransaction]:
    """执行抓取和详情补充,返回结果列表."""
    transactions: list[LandTransaction] = []

    click.echo("\n▶ 步骤 1/2: 通过 API 获取列表数据...", err=True)
    click.echo(f"  目标: {max_pages} 页 (每页 10 条)", err=True)
    click.echo(
        "  提示: 此步骤依赖佛山内网 API (fw.ggzy.foshan.gov.cn:8080)", err=True,
    )
    click.echo("        若长时间无响应, 请检查网络连接\n", err=True)

    count = 0
    async for tx in fetch_all(max_pages=max_pages):
        transactions.append(tx)
        count += 1
        _print_list_fetch_progress(count)

    click.echo(f"\n✓ 列表获取完成, 共 {len(transactions)} 条记录", err=True)

    if not transactions:
        click.echo("\n⚠  未获取到任何数据, 请检查:", err=True)
        click.echo("   1. 网络是否可访问佛山公共资源交易网站", err=True)
        click.echo(
            "   2. curl.exe 是否可用 (命令行运行 curl --version 验证)", err=True,
        )
        click.echo("   3. 是否在佛山内网环境下", err=True)
        return []

    if not no_detail:
        click.echo(
            "\n▶ 步骤 2/2: 通过 HTTP 获取详情页 (补充交易土地面积)...", err=True,
        )
        await enrich_with_details(transactions)
        filled = sum(1 for tx in transactions if tx.transaction_area)
        click.echo(
            f"\n✓ 详情页抓取完成, transaction_area 有值: {filled}/{len(transactions)} 条",
            err=True,
        )
    else:
        click.echo("\n▶ 步骤 2/2: 已跳过详情页抓取 (--no-detail)", err=True)
        click.echo("  提示: transaction_area 字段为空", err=True)
        click.echo("        可重新运行不加 --no-detail 补充", err=True)

    return transactions


@click.command()
@click.option(
    "--max-pages",
    "-p",
    default=DEFAULT_MAX_PAGES,
    type=int,
    help="最大页数 (默认: 10)",
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
    "--no-detail",
    is_flag=True,
    default=False,
    help="跳过详情页抓取 (仅获取列表字段)",
)
def main(max_pages: int, output_dir: Path | None, no_detail: bool) -> None:
    """佛山土地交易信息爬虫 (JSON API 分页抓取 + 详情页补充).

    通过 JSON API 分页获取土地交易列表,再访问详情页补充交易面积等字段.
    支持导出 JSON、CSV 和 Excel 格式.
    """
    if max_pages < 1:
        click.echo("错误: max-pages 必须 >= 1", err=True)
        sys.exit(2)

    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    _print_header(max_pages, output_dir, no_detail)

    async def run() -> None:
        transactions = await _fetch_and_enrich(max_pages, no_detail)

        if not transactions:
            return

        click.echo("\n▶ 导出数据...", err=True)
        json_path, csv_path, excel_path = export_all(transactions, output_dir)
        _print_result(json_path, csv_path, excel_path, len(transactions))

    try:
        asyncio.run(run())
    except Exception as e:
        log.error("scraper_failed", error=str(e))
        click.echo(f"\n✗ 抓取失败: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
