"""Playwright 爬虫服务."""

import asyncio
import html
import re
from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlparse

import structlog
from playwright.async_api import FrameLocator, Locator, Page, async_playwright

from foshan_scraper.models import LandTransaction

log = structlog.get_logger()

# 选择器常量
SELECTOR_HISTORY_TRADE_LINK = "body > div > div > div > div.ewb-fa > ul > li.current > a"
SELECTOR_DETAIL_BUTTON = "#lsjyDom > tr:nth-child({i}) > td:nth-child(12) > button"
SELECTOR_NEXT_PAGE = "#page-three ul li:nth-child(9) a"  # 下一页按钮的 CSS 选择器
SELECTOR_OUTER_IFRAME = "iframe[src*='TDJY_BasicInfoFrame.aspx']"
SELECTOR_INNER_IFRAME = "iframe[src*='TDJY_BasicInfoHistory.aspx']"

# 字段选择器
FIELD_SELECTORS = {
    "transaction_date": "#ctl00_cphContent_lblChengJiaoDate",
    "winner": "#ctl00_cphContent_lblJingDeRen",
    "transaction_area": "#ctl00_cphContent_JiaoYiMianJi_222124",
    "transaction_price": "#ctl00_cphContent_lblChengJiaoInfo",
    "land_location": "#ctl00_cphContent_DiKuaiWeiZhi_222124",
    "land_usage": "#ctl00_cphContent_TuDiShiJiYongTu_222124",
}

PAGE_LOAD_TIMEOUT = 60_000  # 60秒超时
CLICK_TIMEOUT = 30_000  # 点击超时
NEXT_PAGE_DELAY = 50  # 等待50秒后点击下一页
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔秒数


def extract_url_from_onclick(onclick: str) -> str | None:
    """从 onclick 属性中可靠提取 URL.

    支持单引号、双引号和 &quot; 包裹的 URL。

    Args:
        onclick: onclick 属性值, 例如 window.open("http://...")

    Returns:
        干净的 URL 或 None
    """
    if not onclick:
        return None

    # 先反转义 HTML 实体
    unescaped = html.unescape(onclick)

    # 正则匹配 http:// 或 https:// 开头的 URL
    # 匹配协议、主机、路径、查询字符串，不包含引号或空白  # noqa: RUF003
    pattern = r'https?://[^\s\'"]+'
    match = re.search(pattern, unescaped)

    if match:
        url = match.group(0)
        # 清理 URL 末尾可能的引号
        url = url.rstrip('"').rstrip("'")
        return url

    return None


def extract_biaodiguid_from_url(url: str) -> str:
    """从 URL 中提取 BiaoDiGuid 参数.

    Args:
        url: 详情页 URL

    Returns:
        BiaoDiGuid 值, 如果不存在则返回空字符串
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        biaodiguid_list = params.get("BiaoDiGuid", [])
        if biaodiguid_list:
            return biaodiguid_list[0]
    except Exception as e:
        log.warning("url_parse_failed", url=url, error=str(e))

    return ""


def is_fields_empty(fields: dict[str, str | None]) -> bool:
    """检查字段是否全为空.

    Args:
        fields: 字段字典

    Returns:
        所有字段都为空返回 True
    """
    return all(v is None or v.strip() == "" for v in fields.values())


async def _wait_for_page_load(page: Page, timeout: int = PAGE_LOAD_TIMEOUT) -> None:
    """等待页面加载完成."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass  # 网络空闲状态可能无法获取, 继续等待
    await asyncio.sleep(2)  # 额外等待确保动态内容加载


async def _goto_with_retry(
    page: Page,
    url: str,
    retries: int = MAX_RETRIES,
) -> bool:
    """带重试的页面导航.

    Args:
        page: Playwright Page 对象
        url: 目标 URL
        retries: 最大重试次数

    Returns:
        是否成功导航
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            log.info("page_goto_attempt", url=url, attempt=attempt)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
            if response and response.ok:
                log.info("page_goto_success", url=url, status=response.status)
                return True
            log.warning("page_goto_bad_response", url=url, status=response.status if response else None)
            last_error = f"HTTP {response.status if response else 'None'}"
        except Exception as e:
            last_error = str(e)
            log.warning("page_goto_failed", url=url, attempt=attempt, error=last_error)

        if attempt < retries:
            log.info("retrying", seconds=RETRY_DELAY, remaining_retries=retries - attempt)
            await asyncio.sleep(RETRY_DELAY)

    log.error("page_goto_exhausted_retries", url=url, error=last_error)
    return False


async def _click_with_retry(
    page: Page,
    selector: str,
    retries: int = MAX_RETRIES,
) -> bool:
    """带重试的点击操作.

    Args:
        page: Playwright Page 对象
        selector: CSS 选择器
        retries: 最大重试次数

    Returns:
        是否成功点击
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            log.info("click_attempt", attempt=attempt)
            # 先尝试普通点击
            try:
                await page.locator(selector).scroll_into_view_if_needed(timeout=5000)
                await page.locator(selector).click(timeout=CLICK_TIMEOUT)
                log.info("click_success")
                return True
            except Exception as e:
                log.info("normal_click_failed", error=str(e))

            # 普通点击失败, 使用 JavaScript 直接点击
            log.info("trying_js_click", selector=selector)
            result = await page.evaluate(f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (el) {{
                        el.click();
                        return true;
                    }}
                    return false;
                }})()
            """)
            if result:
                log.info("js_click_success")
                return True
            last_error = "JS click returned false"
        except Exception as e:
            last_error = str(e)
            log.warning("click_failed", attempt=attempt, error=last_error)

        if attempt < retries:
            log.info("retrying", seconds=RETRY_DELAY, remaining_retries=retries - attempt)
            await asyncio.sleep(RETRY_DELAY)

    log.error("click_exhausted_retries", error=last_error)
    return False

    log.error("click_exhausted_retries", error=last_error)
    return False


async def _extract_fields_from_locator(locator: Locator) -> dict[str, str | None]:
    """从 locator 中提取字段数据."""
    result: dict[str, str | None] = {}

    for field_name, selector in FIELD_SELECTORS.items():
        try:
            element = locator.locator(selector)
            if await element.count() > 0:
                result[field_name] = await element.inner_text()
            else:
                result[field_name] = None
        except Exception as e:
            log.warning("field_extraction_failed", field=field_name, error=str(e))
            result[field_name] = None

    return result


async def _navigate_through_iframes(
    page: Page,
    detail_url: str,
) -> dict[str, str | None] | None:
    """穿越两层 iframe 并提取数据.

    Args:
        page: 父页面
        detail_url: 详情页 URL

    Returns:
        字段数据字典, 失败时返回 None
    """
    extracted: dict[str, str | None] = {}

    try:
        # 在新页面打开详情链接
        new_page = await page.context.new_page()
        try:
            log.info("navigating_to_detail", url=detail_url)
            await new_page.goto(detail_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
            await _wait_for_page_load(new_page)

            # 切换到第一层 iframe
            outer_frame: FrameLocator = new_page.frame_locator(SELECTOR_OUTER_IFRAME)
            # 等待 iframe 加载
            await outer_frame.locator("body").wait_for(timeout=PAGE_LOAD_TIMEOUT)
            log.info("outer_iframe_loaded")

            # 切换到第二层 iframe
            inner_frame: FrameLocator = outer_frame.frame_locator(SELECTOR_INNER_IFRAME)
            await inner_frame.locator("body").wait_for(timeout=PAGE_LOAD_TIMEOUT)
            log.info("inner_iframe_loaded")

            # 在第二层 iframe 中提取数据
            extracted = await _extract_fields_from_locator(inner_frame.locator("body"))
            log.info("fields_extracted", field_count=len([v for v in extracted.values() if v]))

        finally:
            await new_page.close()

    except Exception as e:
        log.warning("iframe_navigation_failed", url=detail_url, error=str(e))
        return None

    return extracted


async def _get_detail_urls_from_page(page: Page) -> list[tuple[int, str]]:
    """从当前页面获取所有详情链接按钮的 URL 和行号."""
    urls: list[tuple[int, str]] = []

    for i in range(1, 11):
        selector = SELECTOR_DETAIL_BUTTON.format(i=i)
        try:
            button = page.locator(selector)
            if await button.count() > 0:
                onclick = await button.get_attribute("onclick")
                if onclick:
                    url = extract_url_from_onclick(onclick)
                    if url:
                        # 验证 URL 格式
                        if url.startswith("http://") or url.startswith("https://"):
                            urls.append((i, url))
                            log.debug("url_extracted", row=i, url=url)
                        else:
                            log.warning("invalid_url_format", row=i, url=url)
        except Exception as e:
            log.warning("button_extraction_failed", row=i, error=str(e))

    return urls


async def _process_detail_url(page: Page, detail_url: str) -> LandTransaction | None:
    """处理单个详情 URL 并返回交易记录.

    Args:
        page: Playwright Page 对象
        detail_url: 详情页 URL

    Returns:
        LandTransaction 对象或 None (失败时)
    """
    log.info("scraping_detail", url=detail_url)
    fields = await _navigate_through_iframes(page, detail_url)

    if fields is None:
        log.warning("skipping_failed_record", url=detail_url, reason="iframe_navigation_failed")
        return None

    if is_fields_empty(fields):
        log.warning("skipping_empty_record", url=detail_url, reason="all_fields_empty")
        return None

    return LandTransaction(
        row_guid=extract_biaodiguid_from_url(detail_url),
        transaction_date=fields.get("transaction_date"),
        winner=fields.get("winner"),
        transaction_area=fields.get("transaction_area"),
        transaction_price=fields.get("transaction_price"),
        land_location=fields.get("land_location"),
        land_usage=fields.get("land_usage"),
        detail_url=detail_url,
    )


async def _click_next_page(page: Page, page_num: int, max_pages: int) -> bool:
    """点击下一页按钮.

    Args:
        page: Playwright Page 对象
        page_num: 当前页码
        max_pages: 最大页数

    Returns:
        是否成功点击并等待了刷新
    """
    if page_num >= max_pages:
        return False

    log.info("step_4_next_page", current_page=page_num)
    next_button = page.locator(SELECTOR_NEXT_PAGE)

    if await next_button.count() == 0:
        log.warning("next_page_button_not_found")
        return False

    current_page_text = await next_button.get_attribute("data-page-index")
    log.info("current_page_index", index=current_page_text)

    # 点击下一页
    clicked = await _click_with_retry(page, SELECTOR_NEXT_PAGE)

    if clicked:
        log.info("next_page_clicked", page=page_num)
        await asyncio.sleep(NEXT_PAGE_DELAY)
        await asyncio.sleep(3)
        return True

    log.warning("next_page_click_failed", page=page_num)
    return False


async def scrape_land_transactions(
    base_url: str,
    max_pages: int = 10,
    headless: bool = True,
) -> AsyncIterator[LandTransaction]:
    """爬取土地交易信息.

    Args:
        base_url: 主页 URL
        max_pages: 最大页数限制
        headless: 是否使用无头模式

    Yields:
        LandTransaction: 每条土地交易记录
    """
    log.info("starting_scraper", base_url=base_url, max_pages=max_pages, headless=headless)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = await context.new_page()

        try:
            # 步骤1: 访问主页 (带重试)
            log.info("step_1_visit_homepage")
            if not await _goto_with_retry(page, base_url):
                log.error("failed_to_load_homepage", url=base_url)
                return  # 退出爬取

            await _wait_for_page_load(page)

            # 步骤2: 访问历史交易链接
            log.info("step_2_visit_history_trade")
            history_link = page.locator(SELECTOR_HISTORY_TRADE_LINK)
            await history_link.click()
            await _wait_for_page_load(page)
            await asyncio.sleep(5)  # 额外等待历史交易页面加载

            # 遍历每一页
            for page_num in range(1, max_pages + 1):
                log.info("processing_page", page=page_num)
                await _wait_for_page_load(page)

                # 步骤3: 获取当前页所有详情链接
                detail_urls = await _get_detail_urls_from_page(page)
                log.info("found_detail_urls", count=len(detail_urls))

                # 遍历每个详情链接
                for _, detail_url in detail_urls:
                    transaction = await _process_detail_url(page, detail_url)
                    if transaction:
                        yield transaction

                # 步骤4: 点击下一页
                if page_num < max_pages and not await _click_next_page(page, page_num, max_pages):
                    break

        finally:
            await browser.close()

    log.info("scraper_completed")
