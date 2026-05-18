# Changelog


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
