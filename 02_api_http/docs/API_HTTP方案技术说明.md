# API + HTTP 方案技术说明

## 1. 任务理解和网站结构

目标是抓取佛山市公共资源交易中心（jy.ggzy.foshan.gov.cn）的土地交易信息，包括：

- 地块位置、成交时间、竞得人、成交地价等列表字段
- 交易土地面积（需从详情页提取）

佛山公共资源交易网站采用 ASP.NET WebForm 技术构建，存在以下技术特征：

- 列表页使用 `Web_GetList` JSON API 提供分页数据
- 详情页嵌套在两层 iframe 中
- 详情页地址使用 HTTP 协议（端口 3680），可能受到本机网络、代理或防火墙影响
- 部分请求返回 502/503 错误

## 2. 为什么增加 API 网络分析方案

最初方案使用 Playwright 浏览器自动化，能够完整渲染 JavaScript 和 iframe，但也存在以下问题：

- **环境依赖重**：需要安装 Playwright 及其浏览器二进制文件
- **运行速度慢**：每个页面都需要启动完整浏览器，开销大
- **资源占用高**：大量并发时内存和 CPU 消耗显著
- **在佛山内网受限**：部分机构环境无法运行 Playwright

因此新增 API + HTTP 方案，通过直接调用网站后端接口，避免浏览器启动和页面渲染开销，同时兼容受限环境。

## 3. Web_GetList API 的请求方式

### 请求地址

```
http://fw.ggzy.foshan.gov.cn:8080/EpointPhoneService_Web/api/web/Web_GetList
```

> 此接口使用 8080 端口，可能受到本机网络、代理、防火墙或服务端安全模块影响。

### 请求方式

POST，Content-Type 为 `application/x-www-form-urlencoded; charset=UTF-8`

### 请求体结构

```json
{
  "ValidateData": "Epoint_WebSerivce_**##0601",
  "paras": {
    "UseType": "tdjyjyls",
    "KeyWord1": "",
    "KeyWord2": "",
    "DDLKey": "",
    "CurrentPageIndex": 1,
    "PageSize": 10
  }
}
```

### 分页参数

- `CurrentPageIndex`：从 1 开始的页码
- `PageSize`：每页记录数，固定为 10

### UseType

`tdjyjyls` 表示"土地交易记录列表"。

### 响应结构

```json
{
  "UserArea": {
    "InfoList": [
      {
        "RowGuid": "uuid",
        "ChengJiaoDate": "成交时间",
        "JingDeRen": "竞得人",
        "ChengJiaoPrice": "成交地价",
        "DiKuaiWeiZhi": "地块位置",
        "TuDiYongTuType1Code": "土地用途",
        "Url": "详情页URL",
        "DiKuaiBianHao": "地块编号",
        "GongYingTypeCode": "供应类型",
        "JiaoYiType": "交易方式",
        "FromPrice": "起始价",
        "Status": "交易状态"
      }
    ]
  }
}
```

### 安全模块问题

API 接口存在服务端安全模块拦截机制。当检测到异常请求模式时，返回内容包含"安全模块"或"Security"关键字，此时会进行重试（最多 3 次，每次间隔 5 秒）。

## 4. API 返回字段与数据模型的映射

| API 字段 | Pydantic 字段 | 说明 |
|----------|--------------|------|
| `RowGuid` | `row_guid` | 记录唯一标识（UUID，必填） |
| `ChengJiaoDate` | `transaction_date` | 成交时间 |
| `JingDeRen` | `winner` | 竞得人 |
| `ChengJiaoPrice` | `transaction_price` | 成交地价 |
| `DiKuaiWeiZhi` | `land_location` | 地块位置 |
| `TuDiYongTuType1Code` | `land_usage` | 土地实际用途 |
| `Url` | `detail_url` | 详情页链接 |
| `DiKuaiBianHao` | `land_code` | 地块编号 |
| `GongYingTypeCode` | `supply_type` | 供应类型 |
| `JiaoYiType` | `trade_type` | 交易方式 |
| `FromPrice` | `start_price` | 起始价 |
| `Status` | `status` | 交易状态 |

`transaction_area`（交易土地面积）不在 API 返回字段中，需要从详情页补充。

## 5. 如何从 API 返回结果获取详情 URL

详情 URL 存储在 API 响应的 `Url` 字段中，格式为：

```
http://jy.ggzy.foshan.gov.cn:3680/TPBank/TDJYZtbMis_FS/Pages/WebShow/TDJY_Frame.aspx?BiaoDiGuid={UUID}
```

`BiaoDiGuid` 参数即 `row_guid`，可作为唯一标识关联列表与详情页数据。

## 6. 如何使用 HTTP 请求详情页

使用 `httpx.AsyncClient` 发送异步 HTTP GET 请求：

```python
async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
    resp = await client.get(detail_url, timeout=30.0)
```

详情页地址使用 HTTP 协议（端口 3680），该端口可能在内网环境下才能访问。

### 502/503 错误处理

检测到 `502 Bad Gateway` 或 `503 Service Unavailable` 时自动重试，最多 3 次，每次间隔 1 秒：

```python
BAD_STATUS_CODES = {502, 503}
```

## 7. 如何解析两层 iframe 地址

佛山详情页使用两层 iframe 嵌套结构：

```
详情页 (TDJY_Frame.aspx)
  └── 第一层 iframe (TDJY_BasicInfoFrame.aspx)
        └── 第二层 iframe (TDJY_BasicInfoHistory.aspx)
              └── 交易面积数据 (#ctl00_cphContent_JiaoYiMianJi_222124)
```

### 第一层 iframe 提取

```python
SELECTOR_OUTER_IFRAME = 'iframe[src*="TDJY_BasicInfoFrame.aspx"]'
outer_src = soup.select_one(SELECTOR_OUTER_IFRAME).get("src")
```

### 第二层 iframe 提取

```python
SELECTOR_INNER_IFRAME = 'iframe[src*="TDJY_BasicInfoHistory.aspx"]'
inner_src = soup.select_one(SELECTOR_INNER_IFRAME).get("src")
```

使用 `urllib.parse.urljoin()` 将相对 URL 转换为绝对 URL。

### 交易面积提取

```python
SELECTOR_TRANSACTION_AREA = "#ctl00_cphContent_JiaoYiMianJi_222124"
elem = soup.select_one(SELECTOR_TRANSACTION_AREA)
area = elem.get_text(strip=True)
```

## 8. 为什么这种方式不同于 Playwright 浏览器自动化

| 维度 | Playwright 方案 | API + HTTP 方案 |
|------|----------------|----------------|
| 执行引擎 | 真实 Chromium 浏览器 | HTTP 协议（curl.exe + httpx） |
| JavaScript 执行 | 完整执行 | 不执行（不适用） |
| iframe 处理 | 浏览器自动处理 | 手动提取 src 属性 |
| 资源消耗 | 高（每个浏览器约 100MB） | 低（纯 HTTP 请求） |
| 速度 | 慢（浏览器启动开销大） | 快（避免浏览器启动和页面渲染开销） |
| 依赖 | Playwright + 浏览器 | 仅 httpx + beautifulsoup4 |
| 环境兼容 | 部分受限 | 广泛兼容 |

本方案通过协议层直接与服务器交互，无需启动浏览器，适用于佛山公共资源交易网站的场景。

## 9. 请求重试、超时、502 和安全模块拦截

### curl.exe 调用（API 列表）

- 通过 `subprocess.run()` 调用系统 `curl.exe`
- 超时时间：35 秒（请求 30 秒 + 缓冲 5 秒）
- 最多重试 3 次，间隔 5 秒
- 响应空或包含"安全模块"关键字时重试

### httpx 调用（详情页）

- 异步 HTTP GET，超时 30 秒
- 502/503 最多重试 3 次，间隔 1 秒
- 连接超时和读取超时统一处理
- 详情页顺序执行，避免对目标服务器造成压力

## 10. 数据去重和完整性验证方法

### 去重机制

API 返回的每条记录有唯一 `RowGuid` 字段，详情页补充面积时，已知 `transaction_area` 的记录会跳过重复请求：

```python
if tx.transaction_area is not None:
    continue
```

### 完整性验证

实际抓取 10 页后验证结果：

- 总记录数：100 条
- 字段数量：14 个（包含 crawled_at）
- `row_guid` 无重复（集合大小 == 列表长度）
- `detail_url` 无重复
- `transaction_area` 100 条均有值
- 已成交：98 条
- 不成交：2 条

不成交记录没有 `transaction_date`、`winner`、`transaction_price` 是正常情况，因为这些字段只在成交后才由系统填写。

## 11. 当前方案的不足和后续改进

### 当前不足

1. **iframe 结构依赖**：若网站改版改变 iframe 层级或 ID，解析器会失效
2. **详情页端口限制**：端口 3680 可能在内网环境才可访问，外网环境下无法补充 `transaction_area`
3. **无并发控制（列表）**：API 列表页是顺序抓取，速度受限于网络延迟
4. **详情页顺序执行**：出于礼貌爬虫考虑设为顺序执行，可改为小并发（2-3）提升速度
5. **无增量同步**：每次运行重新抓取，无 last-modified 或 ETag 支持
6. **无数据持久化**：仅导出文件，不支持数据库存储

### 后续改进

1. 考虑增加增量同步支持（基于 `crawled_at` 字段过滤新记录）
2. 详情页可改为小并发（2-3），提升抓取速度
3. 增加结果缓存（避免重复抓取已获取的详情页）
4. 补充错误重试统计和失败记录单独导出
5. 考虑切换到 SQLite 数据库存储，便于查询
