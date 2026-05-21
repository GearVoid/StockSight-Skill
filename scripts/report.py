#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-click StockSight report generator."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    BOLLResult,
    DataSourceError,
    KDJResult,
    MACDResult,
    NewsItem,
    RSIResult,
    ReportData,
    RiskSignal,
    StockData,
    TechnicalAnalysis,
    TechnicalSignal,
    TrendSummary,
    analyze_technical_indicators,
    detect,
    normalize_quote_data,
)
from formatter import (  # noqa: E402
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)
from news import search_configured_news  # noqa: E402
from providers import (  # noqa: E402
    AShareHistoryDataSource,
    EastMoneyDataSource,
    SinaDataSource,
    TencentDataSource,
    YahooFinanceDataSource,
)

logger = logging.getLogger(__name__)

SNAPSHOT_SCHEMA_VERSION = 1
MIN_TECHNICAL_HISTORY_BARS = 35
T = TypeVar("T")


class ReportBuildError(Exception):
    """Live report generation failed before rendering."""

    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate StockSight Markdown and optional HTML stock reports.",
    )
    parser.add_argument(
        "codes",
        nargs="*",
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
        choices=["auto", "tencent", "yahoo", "sina", "eastmoney"],
        default="auto",
        help="Quote provider. auto uses Tencent, Yahoo, Sina, then EastMoney failover.",
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
        help="Custom report title. When used with --from-snapshot it intentionally changes the rendered title.",
    )
    parser.add_argument(
        "--save-snapshot",
        type=Path,
        help="Save the exact normalized report payload for reproducible rendering.",
    )
    parser.add_argument(
        "--from-snapshot",
        type=Path,
        help="Render from a saved snapshot instead of fetching live quotes, news, or signals.",
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
    if provider == "yahoo":
        return [YahooFinanceDataSource()]
    if provider == "eastmoney":
        return [EastMoneyDataSource()]
    return [TencentDataSource(), YahooFinanceDataSource(), SinaDataSource(), EastMoneyDataSource()]


def _fetch_quotes(codes: Sequence[str], provider: str):
    """Fetch quotes with provider failover and Sina market hints."""
    remaining = list(codes)
    all_data = {}
    used_name = "无可用数据源"
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
            logger.info("板块基准已注入：%d 只", len(benchmarks))
    except Exception as exc:
        logger.warning("板块基准获取失败，将使用同批均值：%s", exc)
    return benchmarks


def _write_text(path: Optional[Path], text: str) -> Optional[Path]:
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.resolve()


def _default_output_path(stock: StockData, suffix: str) -> Path:
    return Path("outputs") / f"{stock.code}-stocksight-report{suffix}"


def _resolve_html_path(args, stock: StockData) -> Path:
    if args.html and args.out:
        return args.out
    return _default_output_path(stock, ".html")


def _dataclass_from_dict(cls: Type[T], payload: Dict[str, Any]) -> T:
    allowed = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in payload.items() if key in allowed})


def _report_to_payload(data: ReportData) -> Dict[str, Any]:
    return {
        "title": data.title,
        "summary": data.summary,
        "stocks": [asdict(stock) for stock in data.stocks],
        "signals": [asdict(signal) for signal in data.signals],
        "data_source": data.data_source,
        "timestamp": data.timestamp,
        "news": [asdict(item) for item in data.news],
        "technical": asdict(data.technical) if data.technical else None,
    }


def _technical_from_payload(payload: Optional[Dict[str, Any]]) -> Optional[TechnicalAnalysis]:
    if not payload:
        return None
    return TechnicalAnalysis(
        macd=_dataclass_from_dict(MACDResult, payload.get("macd") or {}),
        rsi=_dataclass_from_dict(RSIResult, payload.get("rsi") or {}),
        boll=_dataclass_from_dict(BOLLResult, payload.get("boll") or {}),
        kdj=_dataclass_from_dict(KDJResult, payload.get("kdj") or {}),
        signals=[
            _dataclass_from_dict(TechnicalSignal, item)
            for item in payload.get("signals", [])
        ],
        notes=list(payload.get("notes", [])),
        trend=_dataclass_from_dict(TrendSummary, payload.get("trend") or {}),
    )


def _report_from_payload(payload: Dict[str, Any]) -> ReportData:
    return ReportData(
        title=str(payload.get("title", "StockSight Report")),
        summary=str(payload.get("summary", "")),
        stocks=[_dataclass_from_dict(StockData, item) for item in payload.get("stocks", [])],
        signals=[_dataclass_from_dict(RiskSignal, item) for item in payload.get("signals", [])],
        data_source=str(payload.get("data_source", "snapshot")),
        timestamp=str(payload.get("timestamp", "")),
        news=[_dataclass_from_dict(NewsItem, item) for item in payload.get("news", [])],
        technical=_technical_from_payload(payload.get("technical")),
    )


def _save_snapshot(
    path: Path,
    data: ReportData,
    mode: str,
    provider: str,
    failed: Sequence[str],
    quality_notes: Sequence[str],
) -> Path:
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_by": "StockSight-Skill",
        "mode": mode,
        "provider": provider,
        "failed_codes": list(failed),
        "quality_notes": list(quality_notes),
        "report": _report_to_payload(data),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path.resolve()


def _load_snapshot(path: Path) -> Tuple[ReportData, Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read snapshot: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid snapshot JSON: {path}") from exc

    if not isinstance(payload, dict) or "report" not in payload:
        raise ValueError("snapshot must contain a report object")

    data = _report_from_payload(payload["report"])
    data.snapshot_source = str(path)
    if not data.stocks:
        raise ValueError("snapshot contains no stocks")

    meta = {
        "schema_version": payload.get("schema_version"),
        "mode": payload.get("mode", "auto"),
        "provider": payload.get("provider", "snapshot"),
        "failed_codes": list(payload.get("failed_codes", [])),
        "quality_notes": list(payload.get("quality_notes", [])),
    }
    return data, meta


def _has_enough_history(history) -> bool:
    return bool(history and len(history.bars) >= MIN_TECHNICAL_HISTORY_BARS)


def _fetch_history_for_technical(stock: StockData):
    if stock.market in ("sh", "sz"):
        last_history = None
        for source in (EastMoneyDataSource(), AShareHistoryDataSource()):
            history = source.fetch_history(stock.code, days=80)
            if _has_enough_history(history):
                return history
            if history and history.bars:
                last_history = history
        return last_history
    if stock.market == "us":
        return YahooFinanceDataSource().fetch_history(stock.code, days=80)
    return None


def _build_live_report(args, codes: Sequence[str]) -> Tuple[ReportData, str, List[str], List[str]]:
    try:
        stock_map, failed, source_name = _fetch_quotes(codes, args.provider)
    except Exception as exc:
        raise ReportBuildError(f"StockSight fetch failed: {exc}", 2) from exc

    raw_stocks = [stock_map[code] for code in codes if code in stock_map]
    stocks, quality_notes = normalize_quote_data(raw_stocks)
    if not stocks:
        raise ReportBuildError(f"No usable quote data. Failed codes: {', '.join(failed or codes)}", 1)

    signals = detect(stocks, sector_benchmarks=_fetch_sector_benchmarks(stocks, args.provider))
    mode = _select_mode(args.mode, stocks)
    news = _fetch_news(stocks, args.news, args.news_results)

    technical = None
    if mode == "detailed" and len(stocks) == 1:
        stock = stocks[0]
        try:
            history = _fetch_history_for_technical(stock)
            technical = analyze_technical_indicators(history) if history and history.bars else None
        except Exception:
            technical = None
    data = ReportData(
        title=args.title or _default_title(stocks, mode),
        summary=_summary(stocks, len(signals)),
        stocks=stocks,
        signals=signals,
        data_source=source_name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        news=news,
        technical=technical,
    )
    return data, mode, failed, quality_notes


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    codes = _normalize_codes(args.codes)

    failed: List[str] = []
    quality_notes: List[str] = []
    if args.from_snapshot:
        try:
            data, meta = _load_snapshot(args.from_snapshot)
        except ValueError as exc:
            print(f"StockSight snapshot failed: {exc}", file=sys.stderr)
            return 2
        if args.title:
            data.title = args.title
        mode = args.mode if args.mode != "auto" else _select_mode(str(meta.get("mode", "auto")), data.stocks)
        failed = list(meta.get("failed_codes", []))
        quality_notes = list(meta.get("quality_notes", []))
        snapshot_provider = str(meta.get("provider", "snapshot"))
    else:
        if not codes:
            parser.error("at least one stock code is required unless --from-snapshot is used")
        try:
            data, mode, failed, quality_notes = _build_live_report(args, codes)
        except ReportBuildError as exc:
            print(str(exc), file=sys.stderr)
            return exc.exit_code
        snapshot_provider = args.provider

    if args.save_snapshot:
        snapshot_path = _save_snapshot(
            args.save_snapshot,
            data,
            mode=mode,
            provider=snapshot_provider,
            failed=failed,
            quality_notes=quality_notes,
        )
        print(f"Snapshot: {snapshot_path}")

    if mode == "standard":
        markdown = render_standard_report(data)
    else:
        markdown = render_detailed_report(data)

    if not args.no_validate:
        validation = validate_report(markdown, data)
        if not validation.passed:
            print(str(validation), file=sys.stderr)
            return 3

    markdown_path = _write_text(
        args.markdown_out if args.html else args.out,
        markdown,
    )
    if markdown_path is None:
        print(markdown)
    else:
        print(f"Markdown report: {markdown_path}")

    if args.html:
        html_path = _resolve_html_path(args, data.stocks[0])
        resolved_html = _write_text(html_path, render_html_report(data, mode=mode))
        print(f"HTML report: {resolved_html}")

    if failed:
        print(f"Skipped failed codes: {', '.join(failed)}", file=sys.stderr)
    for note in quality_notes:
        print(f"Data quality: {note}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
