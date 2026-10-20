"""api_fetcher 单元测试."""

import json

from foshan_scraper.api_fetcher import _build_payload, _info_list, _parse_item


class TestBuildPayload:
    """_build_payload 测试."""

    def test_parseable_as_json(self) -> None:
        """返回结果可以被 json.loads 解析."""
        payload = _build_payload(page=1, page_size=10)
        parsed = json.loads(payload)
        assert isinstance(parsed, dict)

    def test_validate_data_value(self) -> None:
        """ValidateData 等于 Epoint_WebSerivce_**##0601."""
        payload = _build_payload(page=1, page_size=10)
        parsed = json.loads(payload)
        assert parsed["ValidateData"] == "Epoint_WebSerivce_**##0601"

    def test_no_caret_characters(self) -> None:
        """ValidateData 不包含 ^ 字符."""
        payload = _build_payload(page=1, page_size=10)
        assert "^" not in payload

    def test_use_type_is_tdjyjyls(self) -> None:
        """UseType 为 tdjyjyls."""
        payload = _build_payload(page=1, page_size=10)
        parsed = json.loads(payload)
        assert parsed["paras"]["UseType"] == "tdjyjyls"

    def test_page_parameters(self) -> None:
        """paras 中的 CurrentPageIndex 和 PageSize 正确."""
        payload = _build_payload(page=5, page_size=20)
        parsed = json.loads(payload)
        assert parsed["paras"]["CurrentPageIndex"] == 5
        assert parsed["paras"]["PageSize"] == 20

    def test_separators_compact(self) -> None:
        """使用紧凑分隔符 (无空格)."""
        payload = _build_payload(page=1, page_size=10)
        assert ":1," in payload or ':1,"' in payload


class TestParseItem:
    """_parse_item 测试."""

    def test_basic_parsing(self) -> None:
        """基本解析."""
        raw: dict[str, object] = {
            "RowGuid": "test-guid-123",
            "ChengJiaoDate": "2026/7/27 15:00:02",
            "JingDeRen": "测试公司",
            "ChengJiaoPrice": "地价:15746万元",
            "DiKuaiWeiZhi": "佛山市禅城区",
            "TuDiYongTuType1Code": "居住用地",
            "Url": "http://jy.ggzy.foshan.gov.cn:3680/TPBank/TDJYZtbMis_FS/Pages/WebShow/TDJY_Frame.aspx?BiaoDiGuid=daea5f49-50b8-4a19-b415-117923c489ba",
            "DiKuaiBianHao": "TD2026(CC)WG0005",
            "GongYingTypeCode": "一级市场",
            "JiaoYiType": "网上挂牌",
            "FromPrice": "15746万元",
            "Status": "已成交",
        }
        tx = _parse_item(raw)
        assert tx is not None
        assert tx.row_guid == "test-guid-123"
        assert tx.transaction_date == "2026/7/27 15:00:02"
        assert tx.winner == "测试公司"
        assert tx.land_location == "佛山市禅城区"
        assert tx.land_code == "TD2026(CC)WG0005"
        assert tx.supply_type == "一级市场"
        assert tx.trade_type == "网上挂牌"
        assert tx.start_price == "15746万元"
        assert tx.status == "已成交"

    def test_url_mapped_to_detail_url(self) -> None:
        """Url 正确映射为 detail_url."""
        url = "http://jy.ggzy.foshan.gov.cn:3680/TPBank/TDJYZtbMis_FS/Pages/WebShow/TDJY_Frame.aspx?BiaoDiGuid=abc123"
        raw: dict[str, object] = {"RowGuid": "guid-1", "Url": url}
        tx = _parse_item(raw)
        assert tx is not None
        assert tx.detail_url == url

    def test_missing_row_guid_returns_none(self) -> None:
        """缺少 RowGuid 时返回 None."""
        raw: dict[str, object] = {}
        assert _parse_item(raw) is None

    def test_empty_row_guid_returns_none(self) -> None:
        """RowGuid 为空字符串时返回 None."""
        raw: dict[str, object] = {"RowGuid": "   "}
        assert _parse_item(raw) is None

    def test_missing_optional_fields(self) -> None:
        """可选字段缺失时返回空字符串或 None."""
        raw: dict[str, object] = {"RowGuid": "guid-1"}
        tx = _parse_item(raw)
        assert tx is not None
        assert tx.transaction_date is None
        assert tx.winner is None
        assert tx.land_location is None
        assert tx.detail_url is None


class TestInfoList:
    """_info_list 测试."""

    def test_basic(self) -> None:
        """正常提取 InfoList."""
        raw: dict[str, object] = {
            "UserArea": {"InfoList": [{"RowGuid": "1"}, {"RowGuid": "2"}]}
        }
        assert len(_info_list(raw)) == 2

    def test_missing_user_area(self) -> None:
        """缺少 UserArea 返回空列表."""
        assert _info_list({}) == []

    def test_missing_info_list(self) -> None:
        """缺少 InfoList 返回空列表."""
        assert _info_list({"UserArea": {}}) == []

    def test_filters_non_dict_items(self) -> None:
        """过滤非字典项."""
        raw: dict[str, object] = {
            "UserArea": {"InfoList": [{"RowGuid": "1"}, "not-a-dict", None, {"RowGuid": "3"}]}
        }
        result = _info_list(raw)
        assert len(result) == 2
