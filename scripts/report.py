#!/usr/bin/env python3
"""One-click StockSight report generator."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import DataSourceError, NewsItem, ReportData, StockData, detect, normalize_quote_data  # noqa: E402
from formatter import (  # noqa: E402
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)
from providers import EastMoneyDataSource, SinaDataSource, TencentDataSource  # noqa: E402
from news import search_configured_news  # noqa: E402

import logging

logger = logging.getLogger(__name__)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate StockSight Markdown and optional HTML stock reports.",
    )
    parser.add_argument(
        "codes",
        nargs="+",
        help="Stock codes or tickers, for example 002346 600208 00700 AAPL.",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "standard", "detailed"],
        default="auto",
        help="Report mode. auto uses detailed for one code and standard for multiple codes.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "tencent", "sina", "eastmoney"],
        default="auto",
        help="Quote provider. auto uses Tencent, Sina, then EastMoney failover.",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Search optional news when .sightconfig.json or environment API keys are configured.",
    )
    parser.add_argument(
        "--news-results",
        type=int,
        default=3,
        help="Maximum news items to include when --news is enabled.",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Also generate a self-contained HTML report.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output path. With --html this is the HTML path; otherwise it is the Markdown path.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="Optional Markdown output path. If omitted, Markdown is printed to stdout.",
    )
    parser.add_argument(
        "--title",
        help="Custom report title.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip Markdown validate_report check.",
    )
    return parser


def _normalize_codes(codes: Iterable[str]) -> List[str]:
    return [code.strip() for code in codes if code.strip()]


def _market_hints(codes: Sequence[str]) -> dict:
    """Infer market hints for providers that need ticker disambiguation."""
    hints = {}
    for code in codes:
        if any(ch.isalpha() for ch in code):
            hints[code] = "us"
        elif len(code) == 5:
            hints[code] = "hk"
    return hints


def _source_chain(provider: str):
    if provider == "tencent":
        return [TencentDataSource()]
    if provider == "sina":
        return [SinaDataSource()]
    if provider == "eastmoney":
        return [EastMoneyDataSource()]
    return [TencentDataSource(), SinaDataSource(), EastMoneyDataSource()]


def _fetch_quotes(codes: Sequence[str], provider: str):
    """Fetch quotes with provider failover and Sina market hints."""
    remaining = list(codes)
    all_data = {}
    used_name = "无可用数据"
    hints = _market_hints(codes)

    for source in _source_chain(provider):
        if not remaining:
            break
        try:
            if isinstance(source, SinaDataSource):
                data, failed = source.fetch(remaining, hints)
            else:
                data, failed = source.fetch(remaining)
        except DataSourceError:
            continue
        if data and not all_data:
            used_name = source.name()
        all_data.update(data)
        remaining = failed

    return all_data, remaining, used_name


def _select_mode(mode: str, stocks: Sequence[StockData]) -> str:
    if mode != "auto":
        return mode
    return "detailed" if len(stocks) == 1 else "standard"


def _summary(stocks: Sequence[StockData], signal_count: int) -> str:
    if not stocks:
        return "无可用行情数据。"
    if len(stocks) == 1:
        stock = stocks[0]
        return (
            f"{stock.name}今日报{stock.current_price:.2f}，"
            f"涨跌幅{stock.change_percent:+.2f}%，"
            f"触发{signal_count}个技术异动信号。"
        )
    return f"本次覆盖{len(stocks)}只标的，检测到{signal_count}个技术异动信号。"


def _default_title(stocks: Sequence[StockData], mode: str) -> str:
    if not stocks:
        return "StockSight Report"
    if mode == "detailed":
        stock = stocks[0]
        return f"{stock.name}风险可视化报告"
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{today} 市场异动分析报告"


def _fetch_news(stocks: Sequence[StockData], enabled: bool, max_results: int) -> List[NewsItem]:
    if not enabled or not stocks:
        return []
    return search_configured_news(stocks, max_results=max(1, max_results))


def _fetch_sector_benchmarks(stocks: Sequence[StockData], provider: str) -> dict:
    benchmarks = {}
    if provider not in ("auto", "eastmoney"):
        return benchmarks
    try:
        em = EastMoneyDataSource()
        codes = [s.code for s in stocks]
        result = em.get_sector_benchmarks(codes)
        if result:
            benchmarks = result
            logger.info("板块基准已注入: %d 只", len(benchmarks))
    except Exception as e:
        logger.warning("板块基准获取失败，将使用同批均值: %s", e)
    return benchmarks


def _write_text(path: Optional[Path], text: str) -> Optional[Path]:
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    codes = _normalize_codes(args.codes)
    if not codes:
        parser.error("at least one stock code is required")

    try:
        stock_map, failed, source_name = _fetch_quotes(codes, args.provider)
    except Exception as exc:
        print(f"StockSight fetch failed: {exc}", file=sys.stderr)
        return 2

    raw_stocks = [stock_map[code] for code in codes if code in stock_map]
    stocks, quality_notes = normalize_quote_data(raw_stocks)
    if not stocks:
        print(f"No usable quote data. Failed codes: {', '.join(failed or codes)}", file=sys.stderr)
        return 1

    signals = detect(stocks, sector_benchmarks=_fetch_sector_benchmarks(stocks, args.provider))
    mode = _select_mode(args.mode, stocks)
    news = _fetch_news(stocks, args.news, args.news_results)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = ReportData(
        title=args.title or _default_title(stocks, mode),
        summary=_summary(stocks, len(signals)),
        stocks=stocks,
        signals=signals,
        data_source=source_name,
        timestamp=timestamp,
        news=news,
    )

    if mode == "standard":
        markdown = render_standard_report(data)
    else:
        markdown = render_detailed_report(data)

    if not args.no_validate:
        validation = validate_report(markdown, data)
        if not validation.passed:
            print(str(validation), file=sys.stderr)
            return 3

    markdown_path = _write_text(args.markdown_out if args.html else args.out, markdown)
    if markdown_path is None:
        print(markdown)
    else:
        print(f"Markdown report: {markdown_path}")

    if args.html:
        html_path = args.out or Path("outputs") / f"{stocks[0].code}-stocksight-report.html"
        resolved_html = _write_text(html_path, render_html_report(data, mode=mode))
        print(f"HTML report: {resolved_html}")

    if failed:
        print(f"Skipped failed codes: {', '.join(failed)}", file=sys.stderr)
    for note in quality_notes:
        print(f"Data quality: {note}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
