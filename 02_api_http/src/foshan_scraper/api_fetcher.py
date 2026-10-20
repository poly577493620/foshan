"""JSON API 列表抓取服务 (通过 subprocess 调用 curl.exe 避免安全模块拦截)."""



import json
import subprocess
import time
from collections.abc import AsyncIterator
from typing import cast

import structlog

from foshan_scraper.models import LandTransaction

log = structlog.get_logger()



API_URL = "http://fw.ggzy.foshan.gov.cn:8080/EpointPhoneService_Web/api/web/Web_GetList"



MAX_RETRIES = 3

RETRY_DELAY = 5

REQUEST_TIMEOUT = 30

PAGE_DELAY = 1



CURL_HEADERS = [

    "-H", "Accept: application/json, text/javascript, */*; q=0.01",

    "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",

    "-H", "Cache-Control: no-cache",

    "-H", "Connection: keep-alive",

    "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8",

    "-H", "Origin: http://jy.ggzy.foshan.gov.cn:3680",

    "-H", "Pragma: no-cache",

    "-H", "Referer: http://jy.ggzy.foshan.gov.cn:3680/",

    "-H",

    (

        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

    ),

]





def _build_payload(page: int, page_size: int = 10) -> str:

    """构建 API 请求体 JSON 字符串."""

    return json.dumps(

        {

            "ValidateData": "Epoint_WebSerivce_**##0601",

            "paras": {

                "UseType": "tdjyjyls",

                "KeyWord1": "",

                "KeyWord2": "",

                "DDLKey": "",

                "CurrentPageIndex": page,

                "PageSize": page_size,

            },

        },

        ensure_ascii=False,

        separators=(",", ":"),

    )





def _parse_item(raw: dict[str, object]) -> LandTransaction | None:

    """解析单条 InfoList 记录."""

    row_guid = raw.get("RowGuid")

    if row_guid is None or str(row_guid).strip() == "":

        return None



    return LandTransaction(

        row_guid=str(row_guid),

        transaction_date=str(raw.get("ChengJiaoDate")) if raw.get("ChengJiaoDate") else None,

        winner=str(raw.get("JingDeRen")) if raw.get("JingDeRen") else None,

        transaction_area=None,

        transaction_price=str(raw.get("ChengJiaoPrice")) if raw.get("ChengJiaoPrice") else None,

        land_location=str(raw.get("DiKuaiWeiZhi")) if raw.get("DiKuaiWeiZhi") else None,

        land_usage=str(raw.get("TuDiYongTuType1Code")) if raw.get("TuDiYongTuType1Code") else None,

        detail_url=str(raw.get("Url")) if raw.get("Url") else None,

        land_code=str(raw.get("DiKuaiBianHao")) if raw.get("DiKuaiBianHao") else None,

        supply_type=str(raw.get("GongYingTypeCode")) if raw.get("GongYingTypeCode") else None,

        trade_type=str(raw.get("JiaoYiType")) if raw.get("JiaoYiType") else None,

        start_price=str(raw.get("FromPrice")) if raw.get("FromPrice") else None,

        status=str(raw.get("Status")) if raw.get("Status") else None,

    )





def _info_list(data: dict[str, object]) -> list[dict[str, object]]:

    """从 API 响应中提取 InfoList."""

    user_area = data.get("UserArea")

    if not isinstance(user_area, dict):

        return []

    info = user_area.get("InfoList")

    if not isinstance(info, list):

        return []

    return [item for item in info if isinstance(item, dict)]





def _curl_post(payload: str) -> dict[str, object] | None:

    """通过 curl.exe 调用 API,最多重试3次."""

    cmd = [

        "curl.exe",

        "-s",

        "--max-time", str(REQUEST_TIMEOUT + 5),

        "-X", "POST",

        API_URL,

        *CURL_HEADERS,

        "--data-raw", payload,

        "--insecure",

    ]



    for attempt in range(1, MAX_RETRIES + 1):

        try:

            result = subprocess.run(

                cmd,

                capture_output=True,

                timeout=REQUEST_TIMEOUT + 10,

                check=False,

            )

            if result.returncode != 0:

                err = result.stderr.decode("utf-8", errors="replace")

                log.warning("curl_failed", attempt=attempt, returncode=result.returncode, stderr=err[:200])

                if attempt < MAX_RETRIES:

                    log.info("retrying", delay=RETRY_DELAY, remaining=MAX_RETRIES - attempt)

                    time.sleep(RETRY_DELAY)

                continue



            text = result.stdout.decode("utf-8", errors="replace")



            # 检查空响应

            if not text.strip():

                log.warning("curl_empty_response", attempt=attempt)

                if attempt < MAX_RETRIES:

                    time.sleep(RETRY_DELAY)

                continue



            # 检查安全模块拦截

            if "安全模块" in text or "Serurity" in text:

                log.warning("api_blocked_by_security", attempt=attempt, response=text[:100])

                if attempt < MAX_RETRIES:

                    time.sleep(RETRY_DELAY)

                continue



            # 解析 JSON

            return cast(dict[str, object], json.loads(text))



        except subprocess.TimeoutExpired:

            log.warning("curl_timeout", attempt=attempt)

            if attempt < MAX_RETRIES:

                time.sleep(RETRY_DELAY)

        except Exception as e:

            log.warning("curl_error", attempt=attempt, error=str(e))

            if attempt < MAX_RETRIES:

                time.sleep(RETRY_DELAY)



    log.error("curl_exhausted_retries")

    return None





def _page_delay() -> None:

    """页面间等待."""

    time.sleep(PAGE_DELAY)





async def fetch_all(

    max_pages: int = 10,

) -> AsyncIterator[LandTransaction]:

    """分页抓取所有土地交易记录.



    通过 curl.exe 调用 JSON API,分页获取土地交易列表.



    Args:

        max_pages: 最大页数,每页10条



    Yields:

        LandTransaction: 每条土地交易记录

    """

    log.info("fetch_start", max_pages=max_pages)



    for page_num in range(1, max_pages + 1):

        log.info("fetching_page", page=page_num)



        payload = _build_payload(page_num)

        data = _curl_post(payload)



        if data is None:

            log.warning("page_failed_skipping", page=page_num)

            if page_num < max_pages:

                _page_delay()

            continue



        items = _info_list(data)

        log.info("page_parsed", page=page_num, count=len(items))



        for raw in items:

            tx = _parse_item(raw)

            if tx:

                yield tx



        if page_num < max_pages:

            _page_delay()



    log.info("fetch_complete")
