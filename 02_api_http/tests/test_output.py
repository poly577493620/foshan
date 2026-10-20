"""测试输出服务."""

import json
from pathlib import Path

import pytest

from foshan_scraper.models import LandTransaction
from foshan_scraper.output import export_all, export_to_csv, export_to_json


@pytest.fixture
def sample_transactions() -> list[LandTransaction]:
    """创建测试数据."""
    return [
        LandTransaction(
            row_guid="guid-1",
            transaction_date="2024-01-01",
            winner="公司A",
            transaction_area="1000平",
            transaction_price="500万",
            land_location="禅城区",
            land_usage="住宅",
        ),
        LandTransaction(
            row_guid="guid-2",
            transaction_date="2024-01-02",
            winner="公司B",
            transaction_area="2000平",
            transaction_price="800万",
            land_location="南海区",
            land_usage="商业",
        ),
    ]


def test_export_to_json(tmp_path: Path, sample_transactions: list[LandTransaction]) -> None:
    """测试 JSON 导出."""
    output_file = tmp_path / "test.json"

    export_to_json(sample_transactions, output_file)

    assert output_file.exists()

    with output_file.open(encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]["row_guid"] == "guid-1"
    assert data[0]["winner"] == "公司A"
    assert data[1]["row_guid"] == "guid-2"


def test_export_to_csv(tmp_path: Path, sample_transactions: list[LandTransaction]) -> None:
    """测试 CSV 导出."""
    output_file = tmp_path / "test.csv"

    export_to_csv(sample_transactions, output_file)

    assert output_file.exists()

    with output_file.open(encoding="utf-8") as f:
        lines = f.readlines()

    # 检查表头
    assert "row_guid" in lines[0]
    assert "winner" in lines[0]
    assert "公司A" in lines[1]
    assert "公司B" in lines[2]


def test_export_all(tmp_path: Path, sample_transactions: list[LandTransaction]) -> None:
    """测试同时导出 JSON, CSV 和 Excel."""
    json_path, csv_path, excel_path = export_all(sample_transactions, tmp_path, prefix="test")

    assert json_path.exists()
    assert csv_path.exists()
    assert excel_path.exists()


def test_export_creates_parent_dirs(tmp_path: Path, sample_transactions: list[LandTransaction]) -> None:
    """测试自动创建父目录."""
    output_file = tmp_path / "nested" / "dir" / "test.json"

    export_to_json(sample_transactions, output_file)

    assert output_file.exists()
