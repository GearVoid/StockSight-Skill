# Changelog

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
