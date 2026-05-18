# StockSight Skill

StockSight is a Codex skill for generating Markdown stock anomaly reports across A-shares, Hong Kong equities, and US equities.

## Capabilities

- Market data normalization through Tencent, Sina, and EastMoney providers
- Anomaly detection for volume ratio, turnover rate, and excess return signals
- Standard multi-stock reports and detailed single-stock reports
- Optional news enrichment through Tavily or SerpAPI
- Markdown output validation against the StockSight visual contract

## Usage

1. Copy this folder into your Codex skills directory as `stocksight`.
2. Install dependencies in the runtime environment:

```bash
pip install -r requirements.txt
```

3. Configure optional news providers with `.sightconfig.json` or environment variables.
4. Invoke the `stocksight` skill when asking for stock anomaly analysis or report generation.

## Configuration

Use `config.example.json` as the shape for `.sightconfig.json`.

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

News is optional. If no key is configured, StockSight skips the news section and still renders the core report.

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

Reports and operation suggestions are technical references only and do not constitute investment advice.
