# 佛山土地交易爬虫（Playwright 浏览器自动化方案）

通过 Playwright 启动 Chromium 浏览器，完整渲染 JavaScript，穿越两层 iframe 提取土地交易详情。

## 环境要求

- Python 3.14
- uv（版本管理工具）
- Windows 系统

## 安装

```powershell
cd 01_playwright
uv sync
```

## 首次运行：安装 Chromium 浏览器

```powershell
uv run playwright install chromium
```

## 运行

```powershell
# 默认爬取 10 页（无头模式）
uv run python -m foshan_scraper

# 指定页数和输出目录
uv run python -m foshan_scraper --pages 5 --output ./output

# 可视模式（观察浏览器操作）
uv run python -m foshan_scraper --pages 3 --no-headless

# 查看帮助
uv run python -m foshan_scraper --help
```

## 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | `-u` | 主页 URL | 佛山公共资源交易中心主页 |
| `--pages` | `-p` | 10 | 最大爬取页数（每页 10 条） |
| `--output` | `-o` | `./output` | 输出目录 |
| `--headless` | 无 | True | 无头模式（后台运行，不显示浏览器窗口） |
| `--no-headless` | 无 | False | 可视模式（显示浏览器窗口） |

## 输出文件

抓取结果保存在 `./output/` 目录，包含三个文件：

- `land_transactions.json` — 结构化 JSON
- `land_transactions.csv` — CSV 格式
- `land_transactions.xlsx` — Excel 格式（含中文列标题）

共 9 个字段：记录ID、成交时间、竞得人、交易土地面积、成交地价、地块位置、土地实际用途、详情链接、爬取时间。

## 技术特点

- 启动真实 Chromium 浏览器，完整执行 JavaScript
- 两层 iframe 穿越（TDJY_BasicInfoFrame.aspx → TDJY_BasicInfoHistory.aspx）
- Playwright 异步 API，支持网络超时重试
- 支持可视模式观察爬取过程

## 质量检查

```powershell
uv run ruff check .
uv run mypy src
uv run pytest -q
```
