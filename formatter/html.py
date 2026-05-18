"""HTML report rendering.

The HTML output is a self-contained premium report page. It intentionally uses
plain CSS only: no JavaScript, external images, or template dependencies.
"""

from html import escape
from typing import Dict, List, Sequence, Tuple

from core import ReportData, RiskSignal, StockData
from .base import (
    EmojiMap,
    change_emoji,
    fmt_signal_level,
    format_amount,
    format_change_plain,
    format_price,
    format_turnover,
    format_volume,
    format_volume_ratio,
    market_tag,
    metric_quality_notes,
    render_count_bar,
    render_signal_bar,
    risk_level_counts,
    risk_type_counts,
    signal_level_label,
)


LEVEL_COLORS = {
    1: "#d79b2b",
    2: "#d36b23",
    3: "#c2412d",
}

TYPE_COLORS = [
    "#2454d6",
    "#16794c",
    "#b7791f",
    "#c2412d",
    "#6b46c1",
    "#0f766e",
]


def _html(text: object) -> str:
    """Escape text for HTML output."""
    return escape(str(text), quote=True)


def _target_stock_and_signals(data: ReportData) -> Tuple[StockData, List[RiskSignal]]:
    """Pick the detailed-report target using the same rule as Markdown detailed."""
    if data.signals:
        top_signal = max(data.signals, key=lambda sig: sig.level)
        stock = next(
            (candidate for candidate in data.stocks if candidate.code == top_signal.stock_code),
            data.stocks[0],
        )
        return stock, [sig for sig in data.signals if sig.stock_code == stock.code]
    return data.stocks[0], []


def _metric_card(label: str, value: str, tone: str = "") -> str:
    class_name = f"metric {tone}".strip()
    return (
        f'<div class="{class_name}">'
        f"<span>{_html(label)}</span>"
        f"<strong>{value}</strong>"
        "</div>"
    )


def _pie_gradient(segments: Sequence[Tuple[str, int]]) -> str:
    total = sum(count for _, count in segments)
    if total <= 0:
        return ""

    stops = []
    start = 0.0
    for index, (_, count) in enumerate(segments):
        if count <= 0:
            continue
        color = TYPE_COLORS[index % len(TYPE_COLORS)]
        end = start + count / total * 100
        stops.append(f"{color} {start:.2f}% {end:.2f}%")
        start = end
    return f"background: conic-gradient({', '.join(stops)});"


def _level_pie_gradient(counts: Dict[int, int]) -> str:
    total = sum(counts.values())
    if total <= 0:
        return ""

    stops = []
    start = 0.0
    for level in (1, 2, 3):
        count = counts.get(level, 0)
        if count <= 0:
            continue
        end = start + count / total * 100
        stops.append(f"{LEVEL_COLORS[level]} {start:.2f}% {end:.2f}%")
        start = end
    return f"background: conic-gradient({', '.join(stops)});"


def _risk_distribution_html(signals: Sequence[RiskSignal]) -> str:
    counts = risk_level_counts(signals)
    total = sum(counts.values())
    max_count = max(counts.values(), default=0)

    if total == 0:
        return (
            '<section class="panel">'
            "<h2>风险可视化</h2>"
            '<div class="empty-state">暂无显著异动，风险分布保持平稳。</div>'
            "</section>"
        )

    rows = []
    for level in (1, 2, 3):
        count = counts[level]
        width = 0 if max_count == 0 else count / max_count * 100
        rows.append(
            '<div class="bar-row">'
            f'<span>{_html(signal_level_label(level))}</span>'
            '<div class="bar-track">'
            f'<i style="width:{width:.1f}%; background:{LEVEL_COLORS[level]};"></i>'
            "</div>"
            f"<strong>{count}</strong>"
            f"<em>{render_count_bar(count, max_count)}</em>"
            "</div>"
        )

    pie_style = _level_pie_gradient(counts)
    return (
        '<section class="panel">'
        "<h2>风险可视化</h2>"
        '<div class="chart-grid">'
        '<div class="chart-card">'
        "<h3>风险等级占比</h3>"
        f'<div class="pie" style="{pie_style}"><span>{total}</span></div>'
        '<p class="muted">按 RiskSignal 等级聚合</p>'
        "</div>"
        '<div class="chart-card wide">'
        "<h3>风险分布柱</h3>"
        + "".join(rows)
        + "</div>"
        "</div>"
        "</section>"
    )


def _signal_composition_html(signals: Sequence[RiskSignal]) -> str:
    composition = risk_type_counts(signals)
    if not composition:
        return (
            '<section class="panel">'
            "<h2>信号构成</h2>"
            '<div class="empty-state">暂无显著异动信号。</div>'
            "</section>"
        )

    max_count = max(count for _, count, _ in composition)
    segments = [(risk_type, count) for risk_type, count, _ in composition]
    pie_style = _pie_gradient(segments)

    rows = []
    for index, (risk_type, count, level) in enumerate(composition):
        width = count / max_count * 100
        color = TYPE_COLORS[index % len(TYPE_COLORS)]
        rows.append(
            '<div class="bar-row">'
            f'<span><b style="background:{color};"></b>{_html(risk_type)}</span>'
            '<div class="bar-track">'
            f'<i style="width:{width:.1f}%; background:{color};"></i>'
            "</div>"
            f"<strong>{count}</strong>"
            f"<em>{_html(fmt_signal_level(level))} {render_signal_bar(level)}</em>"
            "</div>"
        )

    return (
        '<section class="panel">'
        "<h2>信号构成</h2>"
        '<div class="chart-grid">'
        '<div class="chart-card">'
        "<h3>类型占比</h3>"
        f'<div class="pie" style="{pie_style}"><span>{sum(count for _, count, _ in composition)}</span></div>'
        '<p class="muted">按风险类型聚合</p>'
        "</div>"
        '<div class="chart-card wide">'
        "<h3>构成柱图</h3>"
        + "".join(rows)
        + "</div>"
        "</div>"
        "</section>"
    )


def _stock_table_html(stocks: Sequence[StockData], signals: Sequence[RiskSignal]) -> str:
    signal_by_code: Dict[str, List[RiskSignal]] = {}
    for sig in signals:
        signal_by_code.setdefault(sig.stock_code, []).append(sig)

    rows = []
    for stock in stocks:
        stock_signals = signal_by_code.get(stock.code, [])
        max_level = max((sig.level for sig in stock_signals), default=0)
        risk_text = "—"
        if stock_signals:
            risk_text = (
                ", ".join(_html(sig.risk_type) for sig in stock_signals)
                + f" {render_signal_bar(max_level)}"
            )
        tag = f" [{market_tag(stock.market)}]" if market_tag(stock.market) else ""
        rows.append(
            "<tr>"
            f"<td>{_html(stock.code)} {_html(stock.name)}{_html(tag)}</td>"
            f"<td>{_html(format_price(stock.current_price, stock.market))}</td>"
            f"<td>{_html(format_change_plain(stock.change_percent))} {change_emoji(stock.change_percent)}</td>"
            f"<td>{_html(format_volume_ratio(stock.volume_ratio))}</td>"
            f"<td>{risk_text}</td>"
            "</tr>"
        )

    return (
        '<section class="panel">'
        "<h2>标的列表</h2>"
        "<table>"
        "<thead><tr><th>股票</th><th>现价</th><th>涨跌幅</th><th>量比</th><th>异动信号</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</section>"
    )


def _risk_notes_html(signals: Sequence[RiskSignal]) -> str:
    if not signals:
        return (
            '<section class="panel">'
            "<h2>风险提示</h2>"
            '<div class="empty-state">当前未检测到显著风险信号。</div>'
            "</section>"
        )

    cards = []
    for sig in signals:
        cards.append(
            '<article class="risk-card">'
            f"<h3>{_html(fmt_signal_level(sig.level))}</h3>"
            f"<p><kbd>{_html(sig.risk_type)}</kbd> {render_signal_bar(sig.level)}</p>"
            f"<p>{_html(sig.description)}（偏离度 {_html(f'{sig.deviation_value:.1f}{sig.deviation_unit}')}）。</p>"
            "</article>"
        )
    return '<section class="panel"><h2>风险提示</h2><div class="risk-grid">' + "".join(cards) + "</div></section>"


def _quality_html(stocks: Sequence[StockData]) -> str:
    notes = metric_quality_notes(stocks)
    if not notes:
        return ""
    items = "".join(f"<li>{_html(note)}</li>" for note in notes)
    return f'<section class="panel quality"><h2>数据完整性</h2><ul>{items}</ul></section>'


def _news_html(data: ReportData) -> str:
    if not data.news:
        return ""
    items = []
    for item in data.news[:5]:
        title = _html(item.title or "—")
        source = _html(item.source or "—")
        time = f" · {_html(item.published_at)}" if item.published_at else ""
        snippet = f"<p>{_html(item.snippet)}</p>" if item.snippet else ""
        if item.url:
            title_html = f'<a href="{_html(item.url)}">{title}</a>'
        else:
            title_html = title
        items.append(
            '<article class="news-item">'
            f"<h3>{title_html}</h3>"
            f'<span>{source}{time}</span>'
            f"{snippet}"
            "</article>"
        )
    return '<section class="panel"><h2>相关资讯</h2>' + "".join(items) + "</section>"


def _style() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f3f6fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d8e0ec;
      --danger: #c2412d;
      --accent: #2454d6;
      --shadow: 0 24px 70px rgba(23, 32, 51, 0.09);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.62;
    }
    main { width: min(1120px, calc(100% - 32px)); margin: 32px auto 56px; }
    header {
      border-radius: 8px;
      padding: 34px 38px;
      color: white;
      background: linear-gradient(135deg, #172033 0%, #253858 58%, #f8fafc 58.2%, #f8fafc 100%);
      box-shadow: var(--shadow);
    }
    h1 { margin: 0 0 12px; font-size: 34px; letter-spacing: 0; }
    h2 { margin: 0 0 18px; font-size: 21px; }
    h3 { margin: 0 0 8px; font-size: 15px; }
    .summary { width: min(760px, 100%); margin: 0; color: rgba(255,255,255,.86); }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0 0;
    }
    .metric, .panel, .chart-card, .risk-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .metric { padding: 12px; color: var(--ink); }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 4px; font-size: 17px; }
    .metric.danger strong { color: var(--danger); }
    .panel {
      margin-top: 18px;
      padding: 22px;
      box-shadow: 0 12px 32px rgba(23, 32, 51, 0.05);
    }
    .chart-grid {
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 16px;
      align-items: stretch;
    }
    .chart-card { padding: 18px; }
    .pie {
      width: 164px;
      aspect-ratio: 1;
      border-radius: 50%;
      margin: 14px auto;
      display: grid;
      place-items: center;
      box-shadow: inset 0 0 0 18px rgba(255,255,255,.82);
    }
    .pie span { font-size: 28px; font-weight: 800; }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(90px, 170px) 1fr 42px minmax(84px, auto);
      gap: 10px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #edf1f7;
    }
    .bar-row:last-child { border-bottom: 0; }
    .bar-row b {
      display: inline-block;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      margin-right: 8px;
    }
    .bar-track { height: 11px; border-radius: 99px; background: #edf1f7; overflow: hidden; }
    .bar-track i { display: block; height: 100%; border-radius: inherit; }
    .bar-row em { color: var(--muted); font-style: normal; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; }
    th { background: #f0f4fa; color: #344054; }
    tr:last-child td { border-bottom: 0; }
    kbd {
      display: inline-block;
      padding: 2px 7px;
      border: 1px solid #cfd7e6;
      border-bottom-width: 2px;
      border-radius: 6px;
      background: #f8fafc;
      color: #253858;
      font-family: inherit;
      font-size: 13px;
      font-weight: 700;
    }
    .risk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .risk-card { padding: 14px; }
    .quality { border-left: 4px solid var(--accent); }
    .empty-state { padding: 16px; border-radius: 8px; background: #f8fafc; color: var(--muted); }
    .news-item { padding: 12px 0; border-bottom: 1px solid var(--line); }
    .news-item:last-child { border-bottom: 0; }
    .news-item span, .muted, footer { color: var(--muted); font-size: 13px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    footer { margin-top: 14px; padding: 0 4px; }
    @media (max-width: 820px) {
      main { width: 100%; margin: 0; }
      header { border-radius: 0; background: #172033; padding: 26px 18px; }
      h1 { font-size: 26px; }
      .metric-grid, .chart-grid { grid-template-columns: 1fr; }
      .panel { border-radius: 0; margin-top: 12px; }
      .bar-row { grid-template-columns: 1fr; gap: 6px; }
      table { display: block; overflow-x: auto; }
    }
    """


def render_html_report(data: ReportData, mode: str = "detailed") -> str:
    """Render a full self-contained HTML report.

    Args:
        data: ReportData packet used by Markdown renderers.
        mode: "detailed" for a single-stock deep dive, "standard" for all stocks.

    Returns:
        Complete HTML document string.
    """
    if not data.stocks:
        title = _html(data.title or "StockSight Report")
        return (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{title}</title></head><body>无可用数据生成报告</body></html>"
        )

    selected_mode = mode if mode in {"standard", "detailed"} else "detailed"
    if selected_mode == "detailed":
        stock, visible_signals = _target_stock_and_signals(data)
        visible_stocks = [stock]
        title = f"{stock.name} ({stock.code}) 深度分析报告"
    else:
        visible_stocks = data.stocks
        visible_signals = data.signals
        title = data.title

    top_level = max((sig.level for sig in visible_signals), default=0)
    tone = "danger" if top_level >= 3 else ""
    first_stock = visible_stocks[0]
    subtitle = data.summary or (
        f"{first_stock.name} 今日收 {format_price(first_stock.current_price, first_stock.market)}，"
        f"涨跌幅 {format_change_plain(first_stock.change_percent)}。"
    )

    metric_cards = [
        _metric_card("覆盖标的", str(len(visible_stocks))),
        _metric_card("异动信号", str(len(visible_signals)), tone),
        _metric_card("最高风险", fmt_signal_level(top_level) if top_level else "平稳", tone),
        _metric_card("数据源", _html(data.data_source)),
        _metric_card("更新时间", _html(data.timestamp)),
    ]

    price_panel = ""
    if selected_mode == "detailed":
        price_panel = (
            '<section class="panel">'
            "<h2>核心指标</h2>"
            '<div class="metric-grid">'
            + _metric_card("当前价", _html(format_price(first_stock.current_price, first_stock.market)))
            + _metric_card("涨跌幅", f"{_html(format_change_plain(first_stock.change_percent))} {change_emoji(first_stock.change_percent)}", tone)
            + _metric_card("量比", _html(format_volume_ratio(first_stock.volume_ratio)))
            + _metric_card("换手率", _html(format_turnover(first_stock.turnover_rate)))
            + _metric_card("成交额", _html(format_amount(first_stock.amount, first_stock.market)))
            + "</div>"
            f"<p class=\"muted\">成交量：{_html(format_volume(first_stock.volume, first_stock.market))}"
            f" · 市场标签：{_html(market_tag(first_stock.market) or '—')}</p>"
            "</section>"
        )

    body = (
        "<!doctype html>"
        '<html lang="zh-CN">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_html(title)}</title>"
        f"<style>{_style()}</style>"
        "</head>"
        "<body>"
        "<main>"
        "<header>"
        f"<h1>{EmojiMap.ANALYSIS} {_html(title)}</h1>"
        f'<p class="summary">{EmojiMap.REPORT} {_html(subtitle)}</p>'
        '<div class="metric-grid">'
        + "".join(metric_cards)
        + "</div>"
        "</header>"
        + price_panel
        + _risk_distribution_html(visible_signals)
        + _signal_composition_html(visible_signals)
        + _quality_html(visible_stocks)
        + _stock_table_html(visible_stocks, visible_signals)
        + _risk_notes_html(visible_signals)
        + _news_html(data)
        + f"<footer>{EmojiMap.DATA_SOURCE} 数据来源：{_html(data.data_source)} | {EmojiMap.CLOCK} {_html(data.timestamp)}"
        " | 技术指标参考，不构成投资建议。</footer>"
        "</main>"
        "</body>"
        "</html>"
    )
    return body
