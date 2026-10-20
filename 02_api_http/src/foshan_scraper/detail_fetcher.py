"""HTTP + BeautifulSoup 详情页抓取服务."""

import asyncio
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup

from foshan_scraper.models import LandTransaction

log = structlog.get_logger()

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1
DETAIL_DELAY = 1

SELECTOR_OUTER_IFRAME = 'iframe[src*="TDJY_BasicInfoFrame.aspx"]'
SELECTOR_INNER_IFRAME = 'iframe[src*="TDJY_BasicInfoHistory.aspx"]'
SELECTOR_TRANSACTION_AREA = "#ctl00_cphContent_JiaoYiMianJi_222124"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
}

BAD_STATUS_CODES = {502, 503}


def _extract_iframe_src(soup: BeautifulSoup, selector: str) -> str | None:
    """从 HTML 中提取 iframe src 属性."""
    iframe = soup.select_one(selector)
    if iframe:
        src = iframe.get("src")
        if isinstance(src, str):
            return src
    return None


def _extract_area(soup: BeautifulSoup) -> str | None:
    """从第二层 iframe HTML 中提取交易面积."""
    elem = soup.select_one(SELECTOR_TRANSACTION_AREA)
    if elem:
        text = elem.get_text(strip=True)
        if text:
            return text
    return None


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response | None:
    """发送 GET 请求,502/503 时重试.

    Returns:
        Response 或 None (重试耗尽)
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code in BAD_STATUS_CODES:
                log.warning("http_502", url=url, attempt=attempt)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                continue
            if not resp.text.strip():
                log.warning("http_empty", url=url, attempt=attempt)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                continue
            return resp
        except httpx.TimeoutException:
            log.warning("http_timeout", url=url, attempt=attempt)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            log.warning("http_error", url=url, attempt=attempt, error=str(e))
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
    return None


async def fetch_detail_area(
    client: httpx.AsyncClient,
    detail_url: str,
) -> str | None:
    """抓取详情页的土地交易面积.

    通过两层 iframe 遍历提取数据.

    Args:
        client: httpx 异步客户端
        detail_url: 详情页 URL

    Returns:
        交易面积字符串, 失败返回 None
    """
    # 步骤1: 请求详情页
    resp1 = await _get_with_retry(client, detail_url)
    if resp1 is None:
        log.warning("detail_page_failed", url=detail_url)
        return None

    soup1 = BeautifulSoup(resp1.text, "html.parser")

    # 步骤2: 提取第一层 iframe src
    outer_src = _extract_iframe_src(soup1, SELECTOR_OUTER_IFRAME)
    if not outer_src:
        log.warning("outer_iframe_not_found", url=detail_url)
        return None

    outer_url = urljoin(detail_url, outer_src)

    # 步骤3: 请求第一层 iframe
    resp2 = await _get_with_retry(client, outer_url)
    if resp2 is None:
        log.warning("outer_iframe_failed", url=outer_url)
        return None

    soup2 = BeautifulSoup(resp2.text, "html.parser")

    # 步骤4: 提取第二层 iframe src
    inner_src = _extract_iframe_src(soup2, SELECTOR_INNER_IFRAME)
    if not inner_src:
        log.warning("inner_iframe_not_found", url=outer_url)
        return None

    inner_url = urljoin(outer_url, inner_src)

    # 步骤5: 请求第二层 iframe 并提取面积
    resp3 = await _get_with_retry(client, inner_url)
    if resp3 is None:
        log.warning("inner_iframe_failed", url=inner_url)
        return None

    soup3 = BeautifulSoup(resp3.text, "html.parser")
    return _extract_area(soup3)


async def enrich_with_details(
    transactions: list[LandTransaction],
) -> None:
    """批量补充详情页数据 (顺序执行).

    Args:
        transactions: LandTransaction list (in-place)
    """
    if not transactions:
        return

    log.info("enriching_details", total=len(transactions))

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
    ) as client:
        for tx in transactions:
            if tx.transaction_area is not None:
                continue
            if not tx.detail_url:
                continue

            log.info("fetching_detail", guid=tx.row_guid, url=tx.detail_url)
            area = await fetch_detail_area(client, tx.detail_url)

            if area:
                tx.transaction_area = area
                log.info("area_enriched", guid=tx.row_guid, area=area)
            else:
                log.warning("area_fetch_failed", guid=tx.row_guid, url=tx.detail_url)

            await asyncio.sleep(DETAIL_DELAY)

    log.info("enriching_complete")
