"""detail_fetcher HTML 解析单元测试 (不访问真实网站)."""

from bs4 import BeautifulSoup

from foshan_scraper.detail_fetcher import (
    _extract_area,
    _extract_iframe_src,
)


class TestExtractIframeSrc:
    """_extract_iframe_src 测试."""

    def test_extracts_outer_iframe(self) -> None:
        """提取第一层 iframe src."""
        html = '<html><body><iframe src="TDJY_BasicInfoFrame.aspx?guid=123"/></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_iframe_src(soup, 'iframe[src*="TDJY_BasicInfoFrame.aspx"]')
        assert result == "TDJY_BasicInfoFrame.aspx?guid=123"

    def test_extracts_inner_iframe(self) -> None:
        """提取第二层 iframe src."""
        html = '<html><body><iframe src="/TPBank/TDJYZtbMis_FS/Pages/TDJY_BasicInfoHistory.aspx?x=1"/></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_iframe_src(soup, 'iframe[src*="TDJY_BasicInfoHistory.aspx"]')
        assert result == "/TPBank/TDJYZtbMis_FS/Pages/TDJY_BasicInfoHistory.aspx?x=1"

    def test_returns_none_when_not_found(self) -> None:
        """未找到时返回 None."""
        html = "<html><body><iframe src='other.aspx'/></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_iframe_src(soup, 'iframe[src*="TDJY_BasicInfoFrame.aspx"]')
        assert result is None

    def test_returns_none_for_empty_html(self) -> None:
        """空 HTML 返回 None."""
        soup = BeautifulSoup("", "html.parser")
        result = _extract_iframe_src(soup, 'iframe[src*="TDJY_BasicInfoFrame.aspx"]')
        assert result is None

    def test_extracts_with_full_url(self) -> None:
        """提取完整 URL."""
        html = '<html><body><iframe src="http://example.com/path/TDJY_BasicInfoFrame.aspx?a=1"/></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_iframe_src(soup, 'iframe[src*="TDJY_BasicInfoFrame.aspx"]')
        assert result == "http://example.com/path/TDJY_BasicInfoFrame.aspx?a=1"


class TestExtractArea:
    """_extract_area 测试."""

    def test_extracts_area_text(self) -> None:
        """提取交易面积文本."""
        html = '<html><body><span id="ctl00_cphContent_JiaoYiMianJi_222124">12568.50 平方米</span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_area(soup)
        assert result == "12568.50 平方米"

    def test_extracts_strips_whitespace(self) -> None:
        """提取时去除空白字符."""
        html = '<html><body><span id="ctl00_cphContent_JiaoYiMianJi_222124">  9876.12 ㎡  </span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_area(soup)
        assert result == "9876.12 ㎡"

    def test_returns_none_when_element_missing(self) -> None:
        """元素不存在时返回 None."""
        html = "<html><body><div>no area here</div></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_area(soup)
        assert result is None

    def test_returns_none_for_empty_element(self) -> None:
        """空元素返回 None."""
        html = '<html><body><span id="ctl00_cphContent_JiaoYiMianJi_222124"></span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_area(soup)
        assert result is None

    def test_returns_none_for_whitespace_only(self) -> None:
        """仅空白字符返回 None."""
        html = '<html><body><span id="ctl00_cphContent_JiaoYiMianJi_222124">   \n\t  </span></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_area(soup)
        assert result is None
