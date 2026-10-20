"""测试 URL 解析工具函数."""

from foshan_scraper.scraper import (
    extract_biaodiguid_from_url,
    extract_url_from_onclick,
    is_fields_empty,
)


class TestExtractUrlFromOnclick:
    """测试 extract_url_from_onclick 函数."""

    def test_double_quote_url(self) -> None:
        """测试双引号包裹的 URL."""
        onclick = 'window.open("http://example.com/page?id=123")'
        result = extract_url_from_onclick(onclick)
        assert result == "http://example.com/page?id=123"

    def test_single_quote_url(self) -> None:
        """测试单引号包裹的 URL."""
        onclick = "window.open('http://example.com/page?id=456')"
        result = extract_url_from_onclick(onclick)
        assert result == "http://example.com/page?id=456"

    def test_quot_entity_url(self) -> None:
        """测试 &quot; 实体包裹的 URL."""
        onclick = "window.open(&quot;http://example.com/page?id=789&quot;)"
        result = extract_url_from_onclick(onclick)
        assert result == "http://example.com/page?id=789"

    def test_real_world_onclick(self) -> None:
        """测试真实 onclick 示例, 带多余引号前缀."""
        onclick = "window.open(&quot;http://jy.ggzy.foshan.gov.cn:3680/TPBank/TDJYZtbMis_FS/Pages/WebShow/TDJY_Frame.aspx?BiaoDiGuid=daea5f49-50b8-4a19-b415-117923c489ba&quot;);"
        result = extract_url_from_onclick(onclick)
        assert result == (
            "http://jy.ggzy.foshan.gov.cn:3680/TPBank/TDJYZtbMis_FS/Pages/WebShow/TDJY_Frame.aspx"
            "?BiaoDiGuid=daea5f49-50b8-4a19-b415-117923c489ba"
        )
        assert result.startswith("http://")
        assert "&quot;" not in result

    def test_https_url(self) -> None:
        """测试 HTTPS URL."""
        onclick = 'window.open("https://secure.example.com/api")'
        result = extract_url_from_onclick(onclick)
        assert result == "https://secure.example.com/api"

    def test_url_with_multiple_parameters(self) -> None:
        """测试带多个参数的 URL."""
        onclick = "window.open(&quot;http://example.com?a=1&b=2&c=hello&quot;)"
        result = extract_url_from_onclick(onclick)
        assert result.startswith("http://example.com?")
        assert "a=1" in result
        assert "b=2" in result
        assert "c=hello" in result

    def test_none_input(self) -> None:
        """测试 None 输入."""
        result = extract_url_from_onclick(None)
        assert result is None

    def test_empty_string(self) -> None:
        """测试空字符串输入."""
        result = extract_url_from_onclick("")
        assert result is None

    def test_no_url_in_onclick(self) -> None:
        """测试没有 URL 的 onclick."""
        onclick = "someFunction();"
        result = extract_url_from_onclick(onclick)
        assert result is None

    def test_url_no_trailing_quote(self) -> None:
        """测试 URL 末尾没有引号."""
        onclick = 'window.open("http://example.com/page'
        result = extract_url_from_onclick(onclick)
        assert result == "http://example.com/page"


class TestExtractBiaoDiGuidFromUrl:
    """测试 extract_biaodiguid_from_url 函数."""

    def test_extract_biaodiguid(self) -> None:
        """测试提取 BiaoDiGuid."""
        url = "http://example.com/page?BiaoDiGuid=daea5f49-50b8-4a19-b415-117923c489ba&RowGuid=abc123"
        result = extract_biaodiguid_from_url(url)
        assert result == "daea5f49-50b8-4a19-b415-117923c489ba"

    def test_no_biaodiguid(self) -> None:
        """测试 URL 中没有 BiaoDiGuid."""
        url = "http://example.com/page?RowGuid=abc123"
        result = extract_biaodiguid_from_url(url)
        assert result == ""

    def test_empty_url(self) -> None:
        """测试空 URL."""
        result = extract_biaodiguid_from_url("")
        assert result == ""

    def test_none_url(self) -> None:
        """测试 None URL."""
        result = extract_biaodiguid_from_url(None)  # type: ignore[arg-type]
        assert result == ""

    def test_special_characters_in_guid(self) -> None:
        """测试 GUID 中特殊字符."""
        url = "http://example.com?BiaoDiGuid={12345678-1234-1234-1234-123456789abc}"
        result = extract_biaodiguid_from_url(url)
        assert result == "{12345678-1234-1234-1234-123456789abc}"


class TestIsFieldsEmpty:
    """测试 is_fields_empty 函数."""

    def test_all_fields_empty(self) -> None:
        """测试所有字段都为空."""
        fields = {
            "transaction_date": None,
            "winner": None,
            "transaction_area": "",
            "transaction_price": "",
            "land_location": None,
            "land_usage": "   ",
        }
        assert is_fields_empty(fields) is True

    def test_some_fields_filled(self) -> None:
        """测试部分字段有值."""
        fields = {
            "transaction_date": "2024-01-01",
            "winner": None,
            "transaction_area": "",
            "transaction_price": "",
            "land_location": None,
            "land_usage": None,
        }
        assert is_fields_empty(fields) is False

    def test_all_fields_filled(self) -> None:
        """测试所有字段都有值."""
        fields = {
            "transaction_date": "2024-01-01",
            "winner": "测试公司",
            "transaction_area": "1000平",
            "transaction_price": "500万",
            "land_location": "禅城区",
            "land_usage": "住宅",
        }
        assert is_fields_empty(fields) is False

    def test_empty_dict(self) -> None:
        """测试空字典."""
        assert is_fields_empty({}) is True
