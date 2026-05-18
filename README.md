# StockSight Skill

StockSight 是一个给 Codex / agent 使用的股票异动分析 skill，用于获取 A 股、港股、美股行情，检测量比、换手率、收益偏离等技术异动，并生成 Markdown 或 HTML 风格的风险报告。

## 功能

- 通过腾讯财经、新浪财经、东方财富等 provider 标准化行情数据
- 自动清洗明显异常的行情字段，避免坏字段触发误导性信号
- 检测量比偏离、换手率偏高、超额收益异动等信号
- 生成多股票标准报告、单股票详细报告和浏览器可打开的 HTML 报告
- 可选接入 Tavily 或 SerpAPI 聚合公告、财报和异动资讯
- 输出高级 Markdown/HTML：badge、强度条、风险分布、信号构成和折叠资讯
- 使用 `validate_report` 校验 Markdown 报告结构和视觉规范

## 使用方式

1. 将本目录作为 `stocksight` skill 放入 Codex skills 目录。
2. 安装运行依赖：

```bash
pip install -r requirements.txt
```

3. 如需新闻资讯，在 `.sightconfig.json` 或环境变量中配置 API key。
4. 让 agent 使用 `stocksight` skill 生成股票异动分析、跨市场行情报告或 HTML 可视化报告。

一键生成报告：

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

Markdown 报告使用：

- `render_standard_report(data)`：多股票/盘面快报
- `render_detailed_report(data)`：单股票深度分析

HTML 报告使用：

- `render_html_report(data, mode="standard")`
- `render_html_report(data, mode="detailed")`

HTML 输出是完整自包含页面，内置 CSS 柱状图和饼图，不依赖 JavaScript、图片或外部样式。

带新闻聚合：

```bash
python scripts/report.py 002346 --mode detailed --news --html --out reports/002346.html
```

## 配置

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

新闻是可选能力。没有 API key 时，StockSight 会跳过资讯区块，但仍然生成核心行情和风险报告。

## 目录结构

```text
StockSight/
├── SKILL.md
├── core/
├── formatter/
├── news/
├── providers/
├── references/
├── config.example.json
└── requirements.txt
```

## 参考文档

- `references/visual-specs.md`：报告视觉和结构规范
- `references/examples.md`：标准、详细、跨市场和资讯报告示例

## 风险提示

报告中的操作建议、目标价、止损价和风险等级仅基于技术指标和公开资讯整理，不构成投资建议。

---

# StockSight Skill

StockSight is a Codex/agent skill for stock anomaly analysis. It fetches A-share, Hong Kong, and US equity quotes, detects unusual volume ratio, turnover, and return signals, and renders Markdown or HTML risk reports.

## Capabilities

- Normalize market data through Tencent, Sina, and EastMoney providers
- Normalize suspicious quote fields before anomaly detection
- Detect volume-ratio deviation, high turnover, and excess-return anomaly signals
- Generate standard multi-stock reports, detailed single-stock reports, and browser-ready HTML reports
- Optionally aggregate announcements, earnings, and anomaly news through Tavily or SerpAPI
- Produce premium Markdown/HTML with badges, signal bars, risk distribution, signal composition, and collapsible news
- Validate Markdown reports with `validate_report`

## Usage

1. Copy this folder into your Codex skills directory as `stocksight`.
2. Install runtime dependencies:

```bash
pip install -r requirements.txt
```

3. Configure optional news providers with `.sightconfig.json` or environment variables.
4. Invoke the `stocksight` skill for stock anomaly analysis, cross-market reports, or HTML visual reports.

Generate a report with one command:

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

Markdown reports:

- `render_standard_report(data)` for multi-stock or daily reports
- `render_detailed_report(data)` for single-stock deep dives

HTML reports:

- `render_html_report(data, mode="standard")`
- `render_html_report(data, mode="detailed")`

HTML output is a complete self-contained page with built-in CSS bar and pie charts. It does not require JavaScript, images, or external stylesheets.

Generate with news aggregation:

```bash
python scripts/report.py 002346 --mode detailed --news --html --out reports/002346.html
```

## Configuration

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

News is optional. If no key is configured, StockSight skips the news section and still renders the core market and risk report.

## Structure

```text
StockSight/
├── SKILL.md
├── core/
├── formatter/
├── news/
├── providers/
├── references/
├── config.example.json
└── requirements.txt
```

## References

- `references/visual-specs.md` defines the report format contract.
- `references/examples.md` contains standard, detailed, cross-market, and news-enabled examples.

## Disclaimer

Reports, operation suggestions, target prices, stop-loss values, and risk levels are technical references only and do not constitute investment advice.
