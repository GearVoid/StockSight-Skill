---
name: stocksight
description: Agent-ready stock anomaly analyst for A-share, Hong Kong, and US equities. Use when Codex needs to fetch quotes, clean suspicious market fields, detect unusual volume/turnover/return signals, add optional news context, render premium Markdown/HTML/PDF stock reports, or validate StockSight report formatting.
---

# StockSight

Use this skill to produce StockSight stock anomaly reports from market data. Keep the workflow data-first: fetch quotes, detect signals, optionally add news, render premium Markdown or self-contained HTML, then validate Markdown before returning it.

## Environment

Install dependencies before importing network providers:

```bash
pip install -r requirements.txt
```

If dependency installation is unavailable, still use this skill for report formatting when the user provides structured `StockData`-like inputs.

## Workflow

1. Build one or more `StockData` records from the available provider data.
2. Run `detect(stocks)` or `detect_anomalies(stocks)` to produce `RiskSignal` entries.
3. Optionally search news only when an API key is configured. If news lookup fails or returns no results, skip the news section and continue.
4. Create `ReportData` with title, summary, stocks, signals, data source, timestamp, and optional `news`.
5. Render Markdown with `render_standard_report(data)` for multi-stock or daily reports, or `render_detailed_report(data)` for single-stock deep dives.
6. When the user wants a browser-ready report, render HTML with `render_html_report(data, mode="standard"|"detailed")`.
7. Run `validate_report(report_text, data)` for Markdown output and fix formatting issues before presenting the report.

For a one-command path, use `scripts/report.py`:

```bash
python scripts/report.py 002346 --mode detailed --html --out reports/002346.html
```

The script prints Markdown by default, writes HTML when `--html` is set, exports stable PDF through local headless Edge/Chrome when `--pdf` is set, and can fall back to a text PDF in restricted browser environments.
Use `--pdf-engine browser` when the user needs the HTML-preserving renderer, or `--pdf-engine text` when reliability is more important than full visual fidelity.
It skips news unless `--news` is set and a news API key is configured.
It normalizes suspicious quote metrics before detection and uses announcement/earnings/anomaly news queries when news is enabled.

## Provider Guidance

- Use `TencentDataSource` for A-share and Hong Kong quote data when available.
- Use `YahooFinanceDataSource` for US tickers when no paid market-data key is available.
- Use `SinaDataSource` as a fallback quote provider when Yahoo or Tencent cannot return data.
- Use `EastMoneyDataSource` for A-share quotes and optional sector benchmark support.
- Prefer `DataSourceFactory` or `scripts/report.py --provider auto` when chaining multiple providers.

## Configuration

Read `.sightconfig.json` from the current directory, this skill directory, or the user home directory. The top-level key is `stock_sight`; see `config.example.json`.

News providers are optional. Supported API key sources:

- `stock_sight.tavily.api_key` or `TAVILY_API_KEY`
- `stock_sight.serpapi.api_key` or `SERPAPI_API_KEY`

## Output Rules

- Follow the visual and report structure in `references/visual-specs.md` when exact formatting matters.
- Use `references/examples.md` for full standard, detailed, cross-market, and news-enabled examples.
- Use lightweight GitHub-compatible HTML (`<kbd>` and `<details>`) plus Unicode signal bars for Markdown polish.
- Use `render_html_report` for a full browser-ready page with built-in CSS charts; do not hand-write one-off HTML reports as the core output path.
- Put a data source line at the end of every report.
- Do not block the core report on missing news API keys, news provider failures, or empty news results.
- Use `—` for unavailable market metrics such as Hong Kong or US volume ratio.
- Show data-quality notes when a metric is unavailable or clearly outside normal bounds.
- Include a brief investment-risk disclaimer when giving target or stop-loss style reference values.

## Error Handling

- Missing dependency: tell the user to install `requirements.txt`, or continue with formatting only if structured data is already available.
- Missing or invalid quote data: return a short unavailable-data message instead of fabricating values.
- Missing news API key, request failure, or empty news results: skip the news section.
- Invalid stock code: ask for a market-qualified code or a recognizable A-share, Hong Kong, or US ticker.

## File Map

```text
stocksight/
├── SKILL.md
├── core/          # types, config, data-source abstraction, detection
├── formatter/     # standard/detailed report rendering and validation
├── news/          # optional news provider abstraction and implementations
├── providers/     # quote providers
└── references/    # visual contract and examples
```

## Development Notes

- Keep public API names stable: `DataSourceFactory.fetch`, `detect`, `detect_anomalies`, `render_standard_report`, `render_detailed_report`, `render_html_report`, and `validate_report`.
- Install runtime dependencies from `requirements.txt` before importing network providers.
