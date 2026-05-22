# Changelog

## v0.3.1 - 2026-05-22

README presentation refresh release.

### Changed
- Replaced the previous split README screenshots with one full AAPL report screenshot that shows the report flow end to end.
- Bumped the README badge and HTML footer version to `v0.3.1`.

## v0.3.0 - 2026-05-21

Source-chain reproducibility and risk-model clarity release. Reports now separate unusual-move strength from downside risk and can prioritize A-share announcements, filings, and other hard information ahead of generic news.

### Added
- **Data source chain** in report context: live quote source, historical K-line source, fallback status, historical bar count, technical cutoff date, and snapshot state.
- **Hard-information-first news aggregation**: A-share query templates for announcements, filings, earnings previews, risk notices, major events, and shareholder changes.
- **Source/category labeling for context items**: exchange, CnInfo, Eastmoney announcement, company site, investor relations, financial media, and generic search results are ranked and labeled.
- **Company information sections** in Markdown and HTML reports, split into "公司公告与硬信息" and "市场资讯与舆情".
- **Dual risk scoring**: `anomaly_score` explains how unusual the move is, while `risk_score` estimates downside/event risk.
- **Anomaly strength breakdown** in Markdown and HTML: price movement, trading activity, turnover, technical confluence, and event-driven contribution.
- **Snapshot source notes** via `ReportData.source_notes`, preserved by `--save-snapshot` and `--from-snapshot`.

### Changed
- HTML risk gauge now centers on downside risk and explains anomaly strength separately.
- Header metrics now show both "异动强度" and "下行风险".
- A-share limit-up and strong upward moves remain high anomaly events but no longer automatically imply high downside risk.
- Optional news is now treated as company context; missing API keys still skip the section without blocking core reports.
- HTML footer version now follows the project release version.

### Fixed
- Snapshot replay remains compatible with older snapshots that do not contain source-chain notes.
- Local `snapshots/` are ignored to keep generated replay artifacts out of commits.

## v0.2.0 - 2026-05-20

Technical indicator convergence release. MACD/RSI now produce trend summaries and divergence detection.

### Added
- **Trend summary analysis**: MACD alignment (bullish/bearish/turning/neutral), histogram trend (expanding/contracting/flat), and RSI trend state (overbought pullback, oversold bounce, sustained directional moves).
- **Price-MACD divergence detection**: Bearish divergence (price higher high, DIF lower high) and bullish divergence (price lower low, DIF higher low) across the last 30-bar window.
- **TrendSummary dataclass** in core/types.py, integrated into TechnicalAnalysis.
- **Hero judgment banner** in HTML reports: color-coded status badge (偏强/过热/转弱/观察), main risk summary, trend indicators, and next-action guidance. Final judgment now incorporates trend summary data.
- **Data credibility panel** in detailed reports: per-field trust labels (可确认/推导/不可用/历史计算) with confidence summary.
- Four-status final judgment labels in `final_judgment()`: 偏强, 过热, 转弱, 观察.
- Multi-scenario test reports for the hero judgment banner (outputs/judgment-*.html).
- Trend summary CSS cards and responsive hero banner styles.
- Installation and agent usage documentation: AGENTS.md, RELEASE.md, updated README.

### Changed
- `analyze_technical_indicators()` now populates `TechnicalAnalysis.trend` with a `TrendSummary`.
- Divergence signals are auto-injected into the technical signal list for risk display.
- _render_technical_section() in detailed formatter now includes a trend summary table.
- _technical_indicators_html() in HTML charts now includes trend summary cards.
- `final_judgment()` enhanced to use trend data for better status classification.

### Fixed
- Report signal duplication when technical risk signals were added both to data.signals and by _combined_signals().


## v0.1.2 - 2026-05-19

Engineering hygiene and test coverage release.

- Added `.gitattributes` and `# -*- coding: utf-8 -*-` headers to all Python source files to fix garbled Chinese text on Windows GBK systems.
- Renamed Chinese identifier names in `detector.py` (`DetectorThresholds` fields, `_level_from_threshold` params) to English with full backward compat via legacy map.
- Added GitHub Actions CI workflow (Python 3.9/3.10/3.11/3.12 matrix, runs on push/PR).
- Relaxed `urllib3<2` pin to Python 3.9 only via environment marker.
- Added 31 new tests covering Tencent (A-share/HK parsing, fetch mock), Sina (A/HK/US field extraction), EastMoney (secid encoding, single-stock parsing), and news module (aggregator dedup, Tavily/SerpAPI response parsing).
- Test suite grows from 28 to 60 tests.

## v0.1.1 - 2026-05-19

Public GitHub-ready release.

- Added reproducible report snapshots with `--save-snapshot` and `--from-snapshot`.
- Added `examples/snapshot-sample.json` for offline rendering demos.
- Added MIT `LICENSE`, `CONTRIBUTING.md`, issue templates, and README badges.
- Removed the built-in PDF exporter because system font differences made Chinese PDF output unreliable.
- Pinned `urllib3<2` for Python 3.9 compatibility.

## v0.1.0 - 2026-05-18

First public skill release.

- Added the standard `SKILL.md` entrypoint for agent discovery.
- Added A-share, Hong Kong, and US quote provider support.
- Added Markdown and self-contained HTML report rendering.
- Added risk gauge, signal radar, signal composition, risk distribution, and data-quality panels.
- Added optional Tavily and SerpAPI news aggregation.
