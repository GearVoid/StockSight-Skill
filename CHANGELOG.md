# Changelog

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
