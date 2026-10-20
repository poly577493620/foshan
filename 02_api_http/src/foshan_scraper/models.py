"""土地交易数据模型."""

from datetime import datetime

from pydantic import BaseModel, Field


class LandTransaction(BaseModel):
    """土地交易记录."""

    row_guid: str = Field(description="记录唯一标识")
    transaction_date: str | None = Field(default=None, description="成交时间")
    winner: str | None = Field(default=None, description="竞得人")
    transaction_area: str | None = Field(default=None, description="交易土地面积")
    transaction_price: str | None = Field(default=None, description="成交地价")
    land_location: str | None = Field(default=None, description="地块位置")
    land_usage: str | None = Field(default=None, description="土地实际用途")
    detail_url: str | None = Field(default=None, description="详情链接")
    crawled_at: datetime = Field(default_factory=datetime.now, description="爬取时间")

    # JSON API 额外字段
    land_code: str | None = Field(default=None, description="地块编号")
    supply_type: str | None = Field(default=None, description="供应类型")
    trade_type: str | None = Field(default=None, description="交易方式")
    start_price: str | None = Field(default=None, description="起始价")
    status: str | None = Field(default=None, description="交易状态")

    model_config = {"extra": "allow"}
