"""测试数据模型."""

from datetime import datetime

from foshan_scraper.models import LandTransaction


def test_land_transaction_creation() -> None:
    """测试创建土地交易记录."""
    transaction = LandTransaction(
        row_guid="test-guid-123",
        transaction_date="2024-01-15",
        winner="测试公司",
        transaction_area="1000平方米",
        transaction_price="500万元",
        land_location="佛山市禅城区",
        land_usage="住宅用地",
    )

    assert transaction.row_guid == "test-guid-123"
    assert transaction.transaction_date == "2024-01-15"
    assert transaction.winner == "测试公司"
    assert transaction.transaction_area == "1000平方米"
    assert transaction.transaction_price == "500万元"
    assert transaction.land_location == "佛山市禅城区"
    assert transaction.land_usage == "住宅用地"
    assert transaction.detail_url is None
    assert isinstance(transaction.crawled_at, datetime)


def test_land_transaction_optional_fields() -> None:
    """测试可选字段默认为 None."""
    transaction = LandTransaction(row_guid="test-123")

    assert transaction.row_guid == "test-123"
    assert transaction.transaction_date is None
    assert transaction.winner is None
    assert transaction.detail_url is None


def test_land_transaction_extra_fields() -> None:
    """测试允许额外字段."""
    transaction = LandTransaction(
        row_guid="test-123",
        extra_field="允许的额外字段",
    )

    assert transaction.row_guid == "test-123"


def test_land_transaction_serialization() -> None:
    """测试模型序列化."""
    transaction = LandTransaction(
        row_guid="test-123",
        winner="测试公司",
    )

    data = transaction.model_dump()
    assert data["row_guid"] == "test-123"
    assert data["winner"] == "测试公司"
