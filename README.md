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

# 佛山土地交易信息爬虫（API + HTTP 方案）

## 项目用途

抓取佛山市公共资源交易中心的土地交易信息，包括地块位置、竞得人、成交价格、交易土地面积等字段，支持导出 JSON、CSV、Excel 三种格式。

## 工作流程

```
┌─────────────────────────────────────┐
│  1. 调用 Web_GetList JSON API        │
│     (通过 curl.exe, 分页获取列表)     │
│     UseType=tdjyjyls, 每页 10 条     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  2. 遍历列表,提取 detail_url        │
│     详情页 URL (BiaoDiGuid 参数)     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  3. HTTP 请求详情页                 │
│     (httpx + BeautifulSoup)        │
│     两层 iframe 地址提取            │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  4. 从第二层 iframe 提取            │
│     交易土地面积 (transaction_area)  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  5. 导出 JSON / CSV / Excel         │
└─────────────────────────────────────┘
```

**本方案不启动浏览器，不使用 Playwright。** 列表数据通过 JSON API 获取，详情页通过 HTTP 请求和 BeautifulSoup 解析。

## 环境要求

- Python 3.14
- uv（版本管理工具）
- Windows 系统（curl.exe 调用依赖）

## 安装

```powershell
cd 02_api_http
uv sync
```

## 运行

抓取 10 页（默认），同时获取详情页数据：

```powershell
uv run python -m foshan_scraper
```

指定页数和输出目录：

```powershell
uv run python -m foshan_scraper --max-pages 5 --output ./data
```

跳过详情页抓取（仅获取列表字段）：

```powershell
uv run python -m foshan_scraper --no-detail
```

完整参数：

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--max-pages` | `-p` | 10 | 最大抓取页数（每页 10 条） |
| `--output` | `-o` | `./output` | 输出目录路径 |
| `--no-detail` | 无 | False | 跳过详情页抓取，不补充 transaction_area |

## 输出文件

抓取结果保存在 `--output` 指定的目录（默认 `./output`），包含三个文件：

- `land_transactions.json` — 结构化 JSON
- `land_transactions.csv` — CSV 格式（UTF-8，无 BOM）
- `land_transactions.xlsx` — Excel 格式（含中文列标题）

共 14 个字段：

| 字段 | 说明 |
|------|------|
| `row_guid` | 记录唯一标识（UUID） |
| `transaction_date` | 成交时间 |
| `winner` | 竞得人 |
| `transaction_area` | 交易土地面积（平方米） |
| `transaction_price` | 成交地价 |
| `land_location` | 地块位置 |
| `land_usage` | 土地实际用途 |
| `detail_url` | 详情页链接 |
| `crawled_at` | 爬取时间 |
| `land_code` | 地块编号 |
| `supply_type` | 供应类型 |
| `trade_type` | 交易方式 |
| `start_price` | 起始价 |
| `status` | 交易状态（已成交 / 不成交） |

## 质量检查

```powershell
# Ruff 代码风格检查
uv run ruff check .

# Mypy 类型检查
uv run mypy src

# pytest 单元测试
uv run pytest -q
```

## 项目结构

```
02_api_http/
├── src/foshan_scraper/
│   ├── __init__.py
│   ├── __main__.py        # CLI 入口
│   ├── models.py          # Pydantic 数据模型
│   ├── api_fetcher.py     # JSON API 抓取（curl.exe）
│   ├── detail_fetcher.py  # HTTP + BeautifulSoup 详情页解析
│   └── output.py          # JSON/CSV/Excel 导出
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_api_fetcher.py
│   ├── test_detail_fetcher.py
│   ├── test_models.py
│   └── test_output.py
├── output/                # 抓取结果（100 条记录）
├── docs/                 # 技术说明文档
├── evidence/             # 录屏证据
├── pyproject.toml
└── uv.lock
```

## 数据验证结果

已执行 10 页抓取，共 100 条记录验证结果：

- 总记录数：100 条
- 字段数量：14 个
- 交易土地面积（transaction_area）：100 条均有值
- `row_guid` 无重复
- `detail_url` 无重复
- 已成交：98 条
- 不成交：2 条（无成交时间、竞得人、成交价格，属正常情况）
