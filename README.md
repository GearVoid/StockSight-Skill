# StockSight-Skill

**Agent-ready stock anomaly reports with market data, risk signals, and terminal-style visuals.**

一个给 Codex / agent 用的股票异动分析 skill。

把一串股票代码丢进来，它会抓行情、清洗坏数据、识别异动信号，再吐出一份能直接回复用户的 Markdown 报告，或者一页更像金融终端的 HTML / PDF 报告。

它不是“又一个行情脚本”。它更像一个会写盘后快报的分析员：先看数据，再找异常，最后把风险讲清楚。

![TSLA report overview](docs/images/tsla-report-overview.png)

![TSLA risk dashboard and radar](docs/images/tsla-report-risk-gauge.png)

![TSLA report data quality and tables](docs/images/tsla-report-radar.png)

## 亮点

- Agent-ready：标准 `SKILL.md` 入口，Codex / agent 可以发现、触发和使用。
- 跨市场行情：支持 A 股、港股、美股，内置腾讯财经、Yahoo Finance、新浪财经、东方财富等 provider。
- 异动识别：检测量比偏离、换手率异常、收益偏离等技术信号。
- 坏数据防误导：自动清洗明显异常字段，例如不可用换手率会显示为 `—`，不参与风险判断。
- 双形态输出：Markdown 适合 agent 直接回复，HTML/PDF 适合正式报告和分享。
- 高级报告视觉：风险仪表盘、信号雷达、风险分布、信号构成、数据完整性面板。
- 可选资讯聚合：配置 Tavily 或 SerpAPI 后可补充公告、财报、异动新闻。
- 最小测试套件：覆盖 formatter、market helper、Yahoo provider、PDF export 等核心路径。

## 快速开始

安装依赖：

```bash
pip install -r requirements.txt
```

生成一份 HTML 报告：

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

生成美股报告：

```bash
python scripts/report.py TSLA --provider yahoo --mode detailed --html --out reports/TSLA.html
```

生成稳定 PDF：

```bash
python scripts/report.py 002346 --mode detailed --pdf --pdf-out reports/002346.pdf
```

PDF 支持三种引擎：

- `--pdf-engine auto`：默认，优先用本机 Edge/Chrome 渲染 HTML，失败后自动生成 text PDF。
- `--pdf-engine browser`：强制保留 HTML 视觉效果，适合本机浏览器环境稳定时使用。
- `--pdf-engine text`：最稳的文本 PDF，适合受限环境。

## Agent 工作流

1. 获取行情：使用 `TencentDataSource`、`YahooFinanceDataSource`、`SinaDataSource` 或 `EastMoneyDataSource`。
2. 清洗行情：调用 `normalize_quote_data(stocks)`，避免坏字段触发误导性信号。
3. 检测异动：调用 `detect(stocks)` 或 `detect_anomalies(stocks)`。
4. 可选资讯：配置新闻 API key 后调用 `search_configured_news(stocks)`。
5. 渲染报告：Markdown 用 `render_standard_report` / `render_detailed_report`，HTML 用 `render_html_report`。
6. 校验输出：Markdown 用 `validate_report(report_text, data)`。

## Python API

```python
from core import ReportData, detect, normalize_quote_data
from formatter import (
    render_standard_report,
    render_detailed_report,
    render_html_report,
    validate_report,
)
from providers import TencentDataSource, YahooFinanceDataSource
```

稳定接口：

- `DataSourceFactory.fetch`
- `detect` / `detect_anomalies`
- `render_standard_report(data)`
- `render_detailed_report(data)`
- `render_html_report(data, mode="detailed")`
- `validate_report(report_text, data)`

## 配置

新闻是可选能力。没有 API key 时，StockSight-Skill 会跳过资讯区块，但仍然生成核心行情和风险报告。

参考 `config.example.json` 创建 `.sightconfig.json`：

```json
{
  "stock_sight": {
    "news_provider": "tavily",
    "tavily": {
      "api_key": "tvly-xxx"
    },
    "serpapi": {
      "api_key": "serpapi-xxx"
    }
  }
}
```

也可以使用环境变量：

- `TAVILY_API_KEY`
- `SERPAPI_API_KEY`

## 测试

```bash
python -m unittest discover -s tests -v
```

当前最小测试套件覆盖：

- Markdown / HTML formatter
- 报告 validator
- 数据质量清洗
- detector 对不可用字段的处理
- 市场识别 helper
- Yahoo Finance 美股 provider
- PDF export helper

## 目录结构

```text
StockSight-Skill/
├── SKILL.md
├── core/
├── formatter/
├── news/
├── providers/
├── scripts/
├── tests/
├── references/
├── docs/images/
├── config.example.json
└── requirements.txt
```

## 注意

报告中的风险等级、目标价、止损参考和操作建议只基于技术指标与公开信息整理，不构成投资建议。

---

# StockSight-Skill

**Agent-ready stock anomaly reports with market data, risk signals, and terminal-style visuals.**

An agent-ready stock anomaly analysis skill for Codex.

Give it a ticker, and it fetches quotes, cleans suspicious fields, detects unusual signals, then renders a Markdown reply or a polished HTML/PDF report.

This is not just another quote script. It behaves more like a compact market analyst: data first, signal second, report last.

![TSLA report overview](docs/images/tsla-report-overview.png)

![TSLA report risk dashboard and signal radar](docs/images/tsla-report-risk-gauge.png)

![TSLA report data quality and tables](docs/images/tsla-report-radar.png)

## Highlights

- Agent-ready `SKILL.md` entrypoint.
- Cross-market quote support for A-shares, Hong Kong equities, and US tickers.
- Providers for Tencent, Yahoo Finance, Sina, and EastMoney.
- Signal detection for volume ratio, turnover, and return anomalies.
- Data-quality guardrails so suspicious fields do not create misleading risk signals.
- Markdown for direct agent replies, HTML/PDF for polished reports.
- Premium report visuals: risk gauge, signal radar, risk distribution, signal composition, and data-quality panels.
- Optional news aggregation through Tavily or SerpAPI.
- Minimal test suite for the core rendering and data paths.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate an HTML report:

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

Generate a US equity report:

```bash
python scripts/report.py TSLA --provider yahoo --mode detailed --html --out reports/TSLA.html
```

Export a stable PDF:

```bash
python scripts/report.py 002346 --mode detailed --pdf --pdf-out reports/002346.pdf
```

PDF engines:

- `--pdf-engine auto`: default; tries local Edge/Chrome HTML printing, then falls back to text PDF.
- `--pdf-engine browser`: preserves HTML visuals when the local browser environment is stable.
- `--pdf-engine text`: robust text-first PDF for restricted environments.

## Agent Pipeline

1. Fetch quotes with `TencentDataSource`, `YahooFinanceDataSource`, `SinaDataSource`, or `EastMoneyDataSource`.
2. Normalize quotes with `normalize_quote_data(stocks)`.
3. Detect anomalies with `detect(stocks)` or `detect_anomalies(stocks)`.
4. Optionally fetch news with `search_configured_news(stocks)`.
5. Render Markdown or HTML.
6. Validate Markdown with `validate_report(report_text, data)`.

## Public API

```python
from core import ReportData, detect, normalize_quote_data
from formatter import (
    render_standard_report,
    render_detailed_report,
    render_html_report,
    validate_report,
)
from providers import TencentDataSource, YahooFinanceDataSource
```

Stable interfaces:

- `DataSourceFactory.fetch`
- `detect` / `detect_anomalies`
- `render_standard_report(data)`
- `render_detailed_report(data)`
- `render_html_report(data, mode="detailed")`
- `validate_report(report_text, data)`

## Configuration

News is optional. Without an API key, StockSight-Skill skips the news section and still renders the core market and risk report.

Use `config.example.json` as the shape for `.sightconfig.json`:

```json
{
  "stock_sight": {
    "news_provider": "tavily",
    "tavily": {
      "api_key": "tvly-xxx"
    },
    "serpapi": {
      "api_key": "serpapi-xxx"
    }
  }
}
```

Environment variables are also supported:

- `TAVILY_API_KEY`
- `SERPAPI_API_KEY`

## Testing

```bash
python -m unittest discover -s tests -v
```

## Disclaimer

Risk levels, target prices, stop-loss references, and operation suggestions are technical references only and do not constitute investment advice.
