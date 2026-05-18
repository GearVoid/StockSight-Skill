"""HTML report rendering.

The HTML output is a self-contained premium report page. It intentionally uses
plain CSS only: no JavaScript, external images, or template dependencies.
"""

from html import escape
from typing import Dict, List, Optional, Sequence, Tuple
import math

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

VERSION = "2.0"

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

HEADER_GRADIENTS = {
    0: "linear-gradient(135deg, #172033 0%, #1e3a5f 25%, #253858 50%, #1e3a5f 75%, #172033 100%)",
    1: "linear-gradient(135deg, #172033 0%, #3d3a1e 25%, #4a4520 50%, #3d3a1e 75%, #172033 100%)",
    2: "linear-gradient(135deg, #172033 0%, #3d2e1e 25%, #5a3a1a 50%, #3d2e1e 75%, #172033 100%)",
    3: "linear-gradient(135deg, #172033 0%, #3d1e1e 25%, #5a1a1a 50%, #3d1e1e 75%, #172033 100%)",
}


def _html(text: object) -> str:
    return escape(str(text), quote=True)


def _target_stock_and_signals(data: ReportData) -> Tuple[StockData, List[RiskSignal]]:
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


def _change_heat_style(change: float) -> str:
    if change > 5:
        return "background:#16794c;color:white;"
    if change > 2:
        return "background:#22c55e;color:white;"
    if change < -5:
        return "background:#c2412d;color:white;"
    if change < -2:
        return "background:#ef4444;color:white;"
    return ""


def _metric_card_heat(label: str, value: str, change: float) -> str:
    heat = _change_heat_style(change)
    inner_style = f'style="{heat}"' if heat else ""
    return (
        f'<div class="metric heat">'
        f"<span>{_html(label)}</span>"
        f'<strong {inner_style}>{value}</strong>'
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


# =============================================================================
# 风险得分计算
# =============================================================================

def _calculate_risk_score(signals: Sequence[RiskSignal]) -> int:
    if not signals:
        return 10
    level_scores = {0: 10, 1: 35, 2: 65, 3: 85}
    max_level = max((s.level for s in signals), default=0)
    base_score = level_scores.get(max_level, 10)
    if len(signals) > 1:
        base_score = min(base_score + len(signals) * 5, 98)
    return base_score


def _get_risk_status(score: int) -> Tuple[str, str, str]:
    if score < 25:
        return "低风险", "#16794c", "0-25"
    elif score < 50:
        return "较低风险", "#d79b2b", "25-50"
    elif score < 75:
        return "中等偏高风险", "#d36b23", "50-75"
    elif score < 90:
        return "高风险", "#e64a19", "75-90"
    else:
        return "极高风险", "#c2412d", "90-100"


# =============================================================================
# 风险仪表盘
# =============================================================================

def _risk_gauge_html(top_level: int, signals: Sequence[RiskSignal]) -> str:
    score = _calculate_risk_score(signals)
    status_text, status_color, range_text = _get_risk_status(score)

    cx, cy = 260, 252
    arc_r = 174
    bg_r = 190
    sw = 18

    angle_deg = (score / 100) * 180 - 180
    rad = math.radians(angle_deg)

    tip_r = arc_r - 8
    tip_x = cx + tip_r * math.cos(rad)
    tip_y = cy + tip_r * math.sin(rad)

    segments = [
        (0, 25, "#11a36a", "低风险", "0-25"),
        (25, 50, "#7ac943", "较低风险", "25-50"),
        (50, 75, "#f1c40f", "中等偏高", "50-75"),
        (75, 90, "#ff7a1a", "高风险", "75-90"),
        (90, 100, "#ef3b2d", "极高风险", "90-100"),
    ]

    arcs = []
    legend = []
    for start_pct, end_pct, color, label, range_label in segments:
        start_angle = (start_pct / 100) * 180 - 180
        end_angle = (end_pct / 100) * 180 - 180
        x1 = cx + arc_r * math.cos(math.radians(start_angle))
        y1 = cy + arc_r * math.sin(math.radians(start_angle))
        x2 = cx + arc_r * math.cos(math.radians(end_angle))
        y2 = cy + arc_r * math.sin(math.radians(end_angle))
        large_arc = 1 if (end_angle - start_angle) > 180 else 0
        arcs.append(f'<path d="M {x1:.2f} {y1:.2f} A {arc_r} {arc_r} 0 {large_arc} 1 {x2:.2f} {y2:.2f}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="butt"/>')
        legend.append(f'<div class="gauge-legend-item"><span style="background:{color};"></span><strong>{_html(label)}</strong><em>{_html(range_label)}</em></div>')

    tick_marks = []
    for pct in [0, 25, 50, 75, 100]:
        a = (pct / 100) * 180 - 180
        r_a = math.radians(a)
        tx = cx + (bg_r + 6) * math.cos(r_a)
        ty = cy + (bg_r + 6) * math.sin(r_a)
        tick_marks.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" dominant-baseline="middle" class="gauge-tick">{pct}</text>')

    bg_sx = cx - bg_r
    bg_sy = cy
    bg_ex = cx + bg_r
    bg_ey = cy
    needle_start_r = 36
    needle_start_x = cx + needle_start_r * math.cos(rad)
    needle_start_y = cy + needle_start_r * math.sin(rad)

    return (
        '<section class="panel" id="risk-gauge">'
        "<h2>风险仪表盘</h2>"
        '<div class="risk-dashboard-shell">'
        '<div class="gauge-stage">'
        + f'<svg viewBox="0 0 520 360" class="new-gauge-svg" role="img" aria-label="综合风险得分 {score}">'
        + f'<path d="M {bg_sx} {bg_sy} A {bg_r} {bg_r} 0 0 1 {bg_ex} {bg_ey}" fill="none" stroke="#edf1f7" stroke-width="2"/>'
        + "".join(arcs)
        + "".join(tick_marks)
        + f'<line x1="{needle_start_x:.1f}" y1="{needle_start_y:.1f}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" stroke="{status_color}" stroke-width="6" stroke-linecap="round"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="8" fill="#172033" stroke="white" stroke-width="3"/>'
        + '</svg>'
        '</div>'
        + '<aside class="gauge-score-card">'
        + '<span>综合风险得分</span>'
        + f'<strong style="color:{status_color};">{score}</strong>'
        + f'<b style="color:{status_color};">{_html(status_text)}</b>'
        + f'<em>风险区间：{_html(range_text)}</em>'
        + '<p>分数由当前技术异动信号等级和数量推导，仅用于风险观察。</p>'
        + '</aside>'
        + '<div class="gauge-legend-pro">'
        + "".join(legend)
        + '</div>'
        + "</div>"
        + "</section>"
    )


# =============================================================================
# 操作建议决策卡
# =============================================================================

def _decision_card_html(stock: StockData, signals: Sequence[RiskSignal]) -> str:
    price = stock.current_price
    mk = stock.market
    stop_loss = round(price * 0.95, 2)
    target = round(price * 1.056, 2)
    max_level = max((s.level for s in signals), default=0)

    if max_level >= 2:
        action = "持有/观望"
        action_class = "caution"
    elif max_level >= 1:
        action = "可关注"
        action_class = "watch"
    else:
        action = "正常持有"
        action_class = "healthy"

    return (
        '<section class="panel" id="decision">'
        "<h2>操作建议</h2>"
        '<div class="decision-card">'
        '<div class="dc-col dc-loss">'
        '<div class="dc-arrow dc-arrow-down">&#9660;</div>'
        '<span class="dc-label">止损参考</span>'
        f'<strong class="dc-price">{_html(format_price(stop_loss, mk))}</strong>'
        '<span class="dc-note">-5%</span>'
        "</div>"
        '<div class="dc-divider"></div>'
        '<div class="dc-col dc-current">'
        f'<span class="dc-action-badge {action_class}">{_html(action)}</span>'
        '<span class="dc-label">当前价</span>'
        f'<strong class="dc-price dc-price-main">{_html(format_price(price, mk))}</strong>'
        "</div>"
        '<div class="dc-divider"></div>'
        '<div class="dc-col dc-target">'
        '<div class="dc-arrow dc-arrow-up">&#9650;</div>'
        '<span class="dc-label">目标参考</span>'
        f'<strong class="dc-price">{_html(format_price(target, mk))}</strong>'
        '<span class="dc-note">+5.6%</span>'
        "</div>"
        "</div>"
        '<p class="muted dc-disclaimer">以上参考数值基于技术指标计算，不构成投资建议。</p>'
        "</section>"
    )


# =============================================================================
# 信号雷达图
# =============================================================================

def _radar_html(signals: Sequence[RiskSignal], stock: StockData) -> str:
    type_levels: Dict[str, int] = {}
    for sig in signals:
        type_levels[sig.risk_type] = max(type_levels.get(sig.risk_type, 0), sig.level)

    dim_config = [
        ("量比信号", "volume_ratio", stock.volume_ratio, "vr"),
        ("换手信号", "turnover", stock.turnover_rate, "tr"),
        ("涨跌幅信号", "change", stock.change_percent, "ch"),
        ("成交额信号", "amount", stock.amount / 10000000 if stock.amount else 0, "am"),
        ("振幅信号", "amplitude", (stock.high - stock.low) / (stock.prev_close or 1) * 100 if (stock.high and stock.low and stock.prev_close) else 0, "ampl"),
        ("波动信号", "volatility", abs(stock.change_percent), "vol"),
    ]

    cx, cy, r_max = 230, 230, 138

    def hex_points(radius: float) -> str:
        pts = []
        for i in range(6):
            angle = -90 + i * 60
            rad = math.radians(angle)
            x = cx + radius * math.cos(rad)
            y = cy + radius * math.sin(rad)
            pts.append(f"{x:.2f},{y:.2f}")
        return " ".join(pts)

    grid = []
    for r, label in [(0.25, "25"), (0.5, "50"), (0.75, "75"), (1.0, "100")]:
        grid.append(f'<polygon points="{hex_points(r_max * r)}" fill="none" stroke="#e5eaf2" stroke-width="1"/>')
        grid.append(f'<text x="{cx}" y="{cy - r_max * r - 5:.1f}" text-anchor="middle" class="radar-scale">{label}</text>')

    axes = []
    labels = []
    for i in range(6):
        angle = -90 + i * 60
        rad = math.radians(angle)
        x = cx + r_max * math.cos(rad)
        y = cy + r_max * math.sin(rad)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}" stroke="#cbd5e1" stroke-width="1"/>')

        label_offset = 54
        label_x = cx + (r_max + label_offset) * math.cos(rad)
        label_y = cy + (r_max + label_offset) * math.sin(rad)

        anchor = "middle"
        if i == 1 or i == 4 or i == 5:
            if i == 1:
                anchor = "start"
                label_x += 4
            elif i == 4:
                anchor = "end"
                label_x -= 4
            elif i == 5:
                anchor = "end"
                label_x -= 4

        labels.append(f'<text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="{anchor}" dominant-baseline="middle" class="radar-axis-label">{_html(dim_config[i][0])}</text>')

    values = []
    for i, (name, key, val, short) in enumerate(dim_config):
        level = 0
        if key == "volume_ratio":
            if val > 3: level = 3
            elif val > 2: level = 2
            elif val > 1.5: level = 1
        elif key == "turnover":
            if val > 15: level = 3
            elif val > 10: level = 2
            elif val > 5: level = 1
        elif key == "change":
            if abs(val) > 9.8: level = 3
            elif abs(val) > 7: level = 2
            elif abs(val) > 5: level = 1
        elif key in ["amplitude", "volatility"]:
            if val > 8: level = 3
            elif val > 5: level = 2
            elif val > 3: level = 1
        elif key == "amount":
            pass
        values.append(level)

    data_points = []
    baseline_points = []
    for i, (name, key, val, short) in enumerate(dim_config):
        angle = -90 + i * 60
        rad = math.radians(angle)
        r = r_max * (0.35 if values[i] == 1 else 0.62 if values[i] == 2 else 0.88 if values[i] == 3 else 0.18)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        data_points.append(f"{x:.2f},{y:.2f}")
        br = r_max * 0.55
        bx = cx + br * math.cos(rad)
        by = cy + br * math.sin(rad)
        baseline_points.append(f"{bx:.2f},{by:.2f}")

    signal_rows = []
    for i, (name, key, val, short) in enumerate(dim_config):
        level = values[i]
        if level >= 3:
            signal = "偏多" if key in {"volume_ratio", "turnover", "amount"} else "偏空" if stock.change_percent < 0 else "偏多"
            pill = "bull" if signal == "偏多" else "bear"
        elif level >= 2:
            signal = "偏高"
            pill = "watch"
        elif level >= 1:
            signal = "关注"
            pill = "watch"
        else:
            signal = "中性"
            pill = "neutral"
        signal_rows.append(
            '<div class="signal-row">'
            f'<span class="signal-icon signal-{i}">{i + 1}</span>'
            f'<strong>{_html(name)}</strong>'
            f'<em>{_html(_radar_signal_description(key, val, level))}</em>'
            f'<b class="{pill}">{_html(signal)}</b>'
            '</div>'
        )

    return (
        '<section class="panel" id="radar">'
        "<h2>信号雷达</h2>"
        '<div class="radar-dashboard">'
        '<div class="radar-stage">'
        '<svg viewBox="0 0 460 460" class="new-radar-svg" role="img" aria-label="六维信号雷达">'
        + "".join(grid)
        + "".join(axes)
        + f'<polygon points="{" ".join(baseline_points)}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4"/>'
        + f'<polygon points="{" ".join(data_points)}" fill="rgba(36, 84, 214, 0.14)" stroke="#2563eb" stroke-width="2.5"/>'
        + "".join(_radar_dots(data_points))
        + "".join(labels)
        + '</svg>'
        '</div>'
        '<div class="signal-list">'
        + "".join(signal_rows)
        + '</div>'
        '</div>'
        "</section>"
    )


def _radar_dots(points: Sequence[str]) -> List[str]:
    dots = []
    for point in points:
        x, y = point.split(",")
        dots.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#2563eb" stroke="white" stroke-width="2"/>')
    return dots


def _radar_signal_description(key: str, value: float, level: int) -> str:
    if key == "volume_ratio":
        return f"量比 {value:.2f}，{'高于活跃阈值' if level else '活跃度中性'}"
    if key == "turnover":
        return f"换手率 {value:.1f}%，{'交易分歧较高' if level else '交易分歧正常'}"
    if key == "change":
        return f"涨跌幅 {value:+.1f}%，{'价格波动显著' if level else '价格波动中性'}"
    if key == "amount":
        return f"成交额强度 {value:.1f}，资金信号参考"
    if key == "amplitude":
        return f"振幅 {value:.1f}%，{'日内波动偏大' if level else '日内波动正常'}"
    return f"波动强度 {value:.1f}，{'需关注' if level else '中性'}"


# =============================================================================
# 侧边导航
# =============================================================================

_NAV_ITEMS = [
    ("#core", "📊", "核心"),
    ("#price-range", "📈", "价格"),
    ("#vol-price", "🔄", "量价"),
    ("#risk-gauge", "🎯", "仪表"),
    ("#risk-dist", "⚠️", "风险"),
    ("#radar", "📡", "雷达"),
    ("#quality", "✅", "数据"),
    ("#decision", "🎯", "建议"),
]


def _nav_html() -> str:
    items = []
    for href, icon, label in _NAV_ITEMS:
        items.append(
            f'<a class="nav-item" href="{href}" title="{_html(label)}">{icon}</a>'
        )
    return '<nav class="side-nav">' + "".join(items) + "</nav>"


# =============================================================================
# 风险可视化
# =============================================================================

def _risk_distribution_html(signals: Sequence[RiskSignal]) -> str:
    counts = risk_level_counts(signals)
    total = sum(counts.values())
    max_count = max(counts.values(), default=0)

    if total == 0:
        return (
            '<section class="panel" id="risk-dist">'
            "<h2>风险可视化</h2>"
            '<div class="empty-state">暂无显著异动，风险分布保持平稳。</div>'
            "</section>"
        )

    dominant_level = max(counts, key=lambda level: counts[level]) if total else 0
    max_level = max((sig.level for sig in signals), default=0)
    concentration = max_count / total * 100 if total else 0
    danger_ratio = counts[3] / total * 100 if total else 0
    risk_summary = _risk_distribution_summary(max_level, danger_ratio, concentration, total)

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
    insight_cards = [
        ("最高等级", fmt_signal_level(max_level), _risk_level_hint(max_level)),
        ("风险集中度", f"{concentration:.0f}%", f"主要集中在{signal_level_label(dominant_level)}级信号"),
        ("危险占比", f"{danger_ratio:.0f}%", "危险信号越集中，短线不确定性越高"),
        ("触发信号", f"{total} 个", "来自当前检测到的技术异动维度"),
    ]
    return (
        '<section class="panel" id="risk-dist">'
        "<h2>风险可视化</h2>"
        f'<p class="section-brief">{_html(risk_summary)}</p>'
        '<div class="risk-insight-grid">'
        + "".join(
            '<article class="risk-insight-card">'
            f'<span>{_html(label)}</span>'
            f'<strong>{_html(value)}</strong>'
            f'<em>{_html(hint)}</em>'
            '</article>'
            for label, value, hint in insight_cards
        )
        + '</div>'
        '<div class="chart-grid enriched">'
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
        '<div class="risk-explain-list">'
        + "".join(_risk_distribution_explanations(signals))
        + "</div>"
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
    cards = []
    for index, (risk_type, count, level) in enumerate(composition):
        width = count / max_count * 100
        color = TYPE_COLORS[index % len(TYPE_COLORS)]
        related = [sig for sig in signals if sig.risk_type == risk_type]
        top_sig = max(related, key=lambda sig: sig.level)
        deviation = f"{top_sig.deviation_value:.1f}{top_sig.deviation_unit}"
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
        cards.append(
            '<article class="signal-detail-card">'
            f'<div class="signal-detail-head"><span style="background:{color};"></span><strong>{_html(risk_type)}</strong><kbd>{_html(fmt_signal_level(level))}</kbd></div>'
            f'<p>{_html(top_sig.description)}（偏离度 {deviation}）。</p>'
            '<dl>'
            f'<div><dt>影响维度</dt><dd>{_html(_risk_type_dimension(risk_type))}</dd></div>'
            f'<div><dt>观察重点</dt><dd>{_html(_risk_type_watchpoint(risk_type))}</dd></div>'
            f'<div><dt>触发次数</dt><dd>{count} 个</dd></div>'
            '</dl>'
            '</article>'
        )

    return (
        '<section class="panel">'
        "<h2>信号构成</h2>"
        f'<p class="section-brief">{_html(_signal_composition_summary(composition))}</p>'
        '<div class="chart-grid enriched">'
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
        '<div class="signal-detail-grid">'
        + "".join(cards)
        + "</div>"
        "</section>"
    )


def _risk_distribution_summary(max_level: int, danger_ratio: float, concentration: float, total: int) -> str:
    if max_level >= 3:
        return f"当前共有 {total} 个异动信号，最高达到危险级；危险信号占比 {danger_ratio:.0f}%，需要优先确认价格和资金承接。"
    if max_level == 2:
        return f"当前共有 {total} 个异动信号，最高为警告级；风险集中度 {concentration:.0f}%，适合继续观察持续性。"
    return f"当前共有 {total} 个异动信号，最高为关注级；风险仍处于早期观察阶段。"


def _risk_level_hint(level: int) -> str:
    if level >= 3:
        return "短线波动或流动性风险较高"
    if level == 2:
        return "存在明显异动，需要确认持续性"
    if level == 1:
        return "轻度偏离，适合常规跟踪"
    return "未检测到显著风险"


def _risk_distribution_explanations(signals: Sequence[RiskSignal]) -> List[str]:
    if not signals:
        return []
    lines = []
    for sig in sorted(signals, key=lambda item: (-item.level, item.risk_type))[:4]:
        lines.append(
            '<div class="risk-explain-item">'
            f'<strong>{_html(sig.risk_type)}</strong>'
            f'<span>{_html(fmt_signal_level(sig.level))}</span>'
            f'<p>{_html(sig.description)}，偏离度 {sig.deviation_value:.1f}{_html(sig.deviation_unit)}。</p>'
            '</div>'
        )
    return lines


def _signal_composition_summary(composition: Sequence[Tuple[str, int, int]]) -> str:
    top_type, top_count, top_level = composition[0]
    return f"信号主要来自“{top_type}”，共 {top_count} 个，最高等级为 {signal_level_label(top_level)}；下方列出每类信号的影响维度和观察重点。"


def _risk_type_dimension(risk_type: str) -> str:
    if "量比" in risk_type:
        return "成交活跃度"
    if "换手" in risk_type:
        return "筹码交换与资金分歧"
    if "收益" in risk_type or "涨跌" in risk_type:
        return "价格偏离与短线波动"
    return "综合技术异动"


def _risk_type_watchpoint(risk_type: str) -> str:
    if "量比" in risk_type:
        return "观察放量是否持续，以及价格是否同步确认方向"
    if "换手" in risk_type:
        return "观察高换手后价格是否走弱，避免分歧扩大"
    if "收益" in risk_type or "涨跌" in risk_type:
        return "观察次日开盘承接、跌停/涨停打开情况和成交变化"
    return "结合公告、财报和板块走势继续验证"


# =============================================================================
# 标的列表
# =============================================================================

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


# =============================================================================
# 风险提示
# =============================================================================

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


# =============================================================================
# 价格区间卡片
# =============================================================================

def _price_range_html(stock: StockData) -> str:
    low = stock.low
    high = stock.high
    current = stock.current_price
    prev_close = stock.prev_close
    open_price = stock.open_price

    if high <= 0 or low <= 0 or high == low:
        return ""

    def _pct(val: float) -> float:
        return max(0.0, min(100.0, (val - low) / (high - low) * 100))

    current_pct = _pct(current)
    prev_pct = _pct(prev_close) if prev_close > 0 else -1
    open_pct = _pct(open_price) if open_price > 0 else -1

    prev_marker = ""
    if prev_pct >= 0:
        prev_marker = f'<span class="range-marker prev" style="left:{prev_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">昨收 {format_price(prev_close, stock.market)}</span></span>'

    open_marker = ""
    if open_pct >= 0:
        open_marker = f'<span class="range-marker open" style="left:{open_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">开盘 {format_price(open_price, stock.market)}</span></span>'

    current_marker = f'<span class="range-marker current" style="left:{current_pct:.1f}%"><span class="marker-dot"></span><span class="marker-label">现价 {format_price(current, stock.market)}</span></span>'

    amplitude = (high - low) / prev_close * 100 if prev_close > 0 else 0

    return (
        '<section class="panel" id="price-range">'
        "<h2>价格区间</h2>"
        '<div class="price-range-card">'
        f'<div class="range-labels"><span>{_html(format_price(low, stock.market))}</span><span>{_html(format_price(high, stock.market))}</span></div>'
        '<div class="range-track">'
        + prev_marker
        + open_marker
        + current_marker
        + "</div>"
        f'<div class="range-meta"><span>振幅 {amplitude:.1f}%</span><span>区间 {format_price(high - low, stock.market)}</span></div>'
        "</div>"
        "</section>"
    )


# =============================================================================
# 量价关系模块
# =============================================================================

def _volume_price_html(stock: StockData, signals: Sequence[RiskSignal]) -> str:
    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    max_level = max((s.level for s in signals), default=0)

    if change > 2 and vr > 1.5:
        vp_status = "价升量增"
        vp_class = "healthy"
        vp_desc = "看多信号，资金积极介入"
    elif change < -2 and vr > 1.5:
        vp_status = "价跌量增"
        vp_class = "caution"
        vp_desc = "抛压较大，需关注支撑位"
    elif change > 2 and vr < 0.8:
        vp_status = "价升量缩"
        vp_class = "caution"
        vp_desc = "上涨动力不足，谨防假突破"
    elif change < -2 and vr < 0.8:
        vp_status = "价跌量缩"
        vp_class = "neutral"
        vp_desc = "缩量下跌，观望情绪浓厚"
    else:
        vp_status = "量价平稳"
        vp_class = "neutral"
        vp_desc = "量价配合正常，按既定策略执行"

    if max_level >= 3:
        fund_status = "高度异常"
        fund_class = "danger"
        fund_desc = "多项指标异常，需重点监控"
    elif max_level >= 2:
        fund_status = "明显异动"
        fund_class = "caution"
        fund_desc = "量比/换手率异常，需确认持续性"
    elif max_level >= 1:
        fund_status = "轻度偏离"
        fund_class = "watch"
        fund_desc = "轻度偏离，常规关注"
    else:
        fund_status = "正常"
        fund_class = "healthy"
        fund_desc = "各项指标正常"

    vr_width = min(vr / 4.0 * 100, 100) if vr > 0 else 0
    tr_width = min(tr / 25.0 * 100, 100) if tr > 0 else 0

    vr_bar_color = "#c2412d" if vr > 3 else "#d36b23" if vr > 2 else "#d79b2b" if vr > 1.5 else "#16794c"
    tr_bar_color = "#c2412d" if tr > 15 else "#d36b23" if tr > 10 else "#d79b2b" if tr > 5 else "#16794c"

    return (
        '<section class="panel" id="vol-price">'
        "<h2>量价关系</h2>"
        '<div class="vp-grid">'
        '<div class="vp-card">'
        '<div class="vp-header">'
        f'<span class="vp-badge {vp_class}">{_html(vp_status)}</span>'
        "<h3>量价配合</h3>"
        "</div>"
        f"<p>{_html(vp_desc)}</p>"
        '<div class="vp-bars">'
        f'<div class="vp-bar-row"><span>量比</span><div class="vp-bar-track"><i style="width:{vr_width:.0f}%; background:{vr_bar_color};"></i></div><strong>{format_volume_ratio(vr)}</strong></div>'
        f'<div class="vp-bar-row"><span>换手率</span><div class="vp-bar-track"><i style="width:{tr_width:.0f}%; background:{tr_bar_color};"></i></div><strong>{format_turnover(tr)}</strong></div>'
        "</div>"
        "</div>"
        '<div class="vp-card">'
        '<div class="vp-header">'
        f'<span class="vp-badge {fund_class}">{_html(fund_status)}</span>'
        "<h3>资金活跃度</h3>"
        "</div>"
        f"<p>{_html(fund_desc)}</p>"
        '<div class="vp-dimension-grid">'
        f'<div class="vp-dim"><span class="dim-label">涨跌幅</span><strong class="dim-value">{format_change_plain(change)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">量比</span><strong class="dim-value">{format_volume_ratio(vr)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">换手率</span><strong class="dim-value">{format_turnover(tr)}</strong></div>'
        f'<div class="vp-dim"><span class="dim-label">最高风险</span><strong class="dim-value">{fmt_signal_level(max_level) if max_level else "平稳"}</strong></div>'
        "</div>"
        "</div>"
        "</div>"
        "</section>"
    )


# =============================================================================
# 资讯时间线
# =============================================================================

def _news_html(data: ReportData) -> str:
    if not data.news:
        return ""

    items = []
    for item in data.news[:5]:
        title = _html(item.title or "—")
        source = _html(item.source or "—")
        time = _html(item.published_at) if item.published_at else ""
        snippet = f"<p>{_html(item.snippet)}</p>" if item.snippet else ""
        if item.url:
            title_html = f'<a href="{_html(item.url)}">{title}</a>'
        else:
            title_html = title

        items.append(
            '<article class="timeline-item">'
            '<div class="timeline-dot"></div>'
            '<div class="timeline-content">'
            f"<h3>{title_html}</h3>"
            f'<div class="timeline-meta"><span>{source}</span>{f" · <span>{time}</span>" if time else ""}</div>'
            f"{snippet}"
            "</div>"
            "</article>"
        )

    return (
        '<section class="panel" id="news">'
        "<h2>相关资讯</h2>"
        '<div class="timeline">'
        + "".join(items)
        + "</div>"
        "</section>"
    )


# =============================================================================
# 数据完整性面板
# =============================================================================

_METRIC_LABELS = {
    "current_price": "现价",
    "prev_close": "昨收价",
    "open_price": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "volume": "成交量",
    "amount": "成交额",
    "volume_ratio": "量比",
    "turnover_rate": "换手率",
    "change_percent": "涨跌幅",
}


def _assess_metric_status(stock: StockData) -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []

    def _add(attr: str, is_unavailable):
        label = _METRIC_LABELS.get(attr, attr)
        val = getattr(stock, attr, None)
        if val is None:
            results.append((label, "缺失", "missing"))
        elif is_unavailable(val):
            results.append((label, "不可用", "unavailable"))
        else:
            results.append((label, "正常", "ok"))

    _add("current_price", lambda v: v <= 0)
    _add("prev_close", lambda v: v < 0)
    _add("open_price", lambda v: v < 0)
    _add("high", lambda v: v < 0)
    _add("low", lambda v: v < 0)
    _add("volume", lambda v: v < 0)
    _add("amount", lambda v: v < 0)
    _add("volume_ratio", lambda v: v < 0)
    _add("turnover_rate", lambda v: v <= 0 or v > 100)
    _add("change_percent", lambda v: False)

    return results


def _quality_html(stocks: Sequence[StockData]) -> str:
    all_statuses: List[Tuple[str, str, str]] = []
    notes = metric_quality_notes(stocks)

    for stock in stocks:
        all_statuses.extend(_assess_metric_status(stock))

    ok_count = sum(1 for _, status, _ in all_statuses if status == "正常")
    total = len(all_statuses)
    pct = ok_count / total * 100 if total > 0 else 100

    if pct >= 100 and not notes:
        integrity_class = "full"
    elif pct >= 80:
        integrity_class = "partial"
    else:
        integrity_class = "degraded"

    ring_gradient = ""
    if total > 0:
        ok_end = pct
        ring_gradient = f"background: conic-gradient(#16794c 0% {ok_end:.1f}%, #edf1f7 {ok_end:.1f}% 100%);"

    items = []
    for label, status, css_class in all_statuses:
        icon = "✓" if status == "正常" else "✗" if status == "缺失" else "—"
        items.append(
            f'<div class="qi-item {css_class}"><span class="qi-icon">{icon}</span><span class="qi-label">{_html(label)}</span><span class="qi-status">{_html(status)}</span></div>'
        )

    note_items = ""
    if notes:
        note_items = '<div class="qi-notes">' + "".join(f"<p>{_html(n)}</p>" for n in notes) + "</div>"

    return (
        '<section class="panel quality-panel" id="quality">'
        "<h2>数据完整性</h2>"
        '<div class="qi-grid">'
        f'<div class="qi-ring"><div class="qi-ring-inner" style="{ring_gradient}"><span>{ok_count}/{total}</span></div><p class="muted">指标可用率</p></div>'
        '<div class="qi-items">'
        + "".join(items)
        + "</div>"
        + note_items
        + "</div>"
        "</section>"
    )


# =============================================================================
# CSS
# =============================================================================

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
    main { width: min(1120px, calc(100% - 32px)); margin: 32px auto 56px; position: relative; }

    /* ---- Hero 头部动态渐变 ---- */
    @keyframes gradient-shift {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    header {
      border-radius: 8px;
      padding: 34px 38px;
      color: white;
      background-size: 200% 200%;
      animation: gradient-shift 8s ease infinite;
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
    .metric strong { display: block; margin-top: 4px; font-size: 17px; border-radius: 4px; padding: 0 2px; }
    .metric.danger strong { color: var(--danger); }

    /* ---- 涨跌幅热力色带 ---- */
    .metric.heat strong {
      display: inline-block;
      border-radius: 6px;
      padding: 2px 8px;
      margin-top: 4px;
    }

    /* ---- 面板入场动画 ---- */
    @keyframes fade-up {
      from { opacity: 0; transform: translateY(18px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .panel {
      margin-top: 18px;
      padding: 22px;
      box-shadow: 0 12px 32px rgba(23, 32, 51, 0.05);
      animation: fade-up 0.5s ease both;
    }
    .panel:nth-of-type(1) { animation-delay: 0s; }
    .panel:nth-of-type(2) { animation-delay: 0.08s; }
    .panel:nth-of-type(3) { animation-delay: 0.16s; }
    .panel:nth-of-type(4) { animation-delay: 0.24s; }
    .panel:nth-of-type(5) { animation-delay: 0.32s; }
    .panel:nth-of-type(6) { animation-delay: 0.40s; }
    .panel:nth-of-type(7) { animation-delay: 0.48s; }
    .panel:nth-of-type(8) { animation-delay: 0.56s; }
    .panel:nth-of-type(9) { animation-delay: 0.64s; }
    .panel:nth-of-type(10) { animation-delay: 0.72s; }
    @media (prefers-reduced-motion: reduce) {
      .panel { animation: none; }
      header { animation: none; }
    }

    .chart-grid {
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 16px;
      align-items: stretch;
    }
    .chart-grid.enriched { margin-top: 16px; }
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
    .empty-state { padding: 16px; border-radius: 8px; background: #f8fafc; color: var(--muted); }
    .section-brief {
      margin: -4px 0 14px;
      color: #344054;
      font-size: 14px;
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }
    .risk-insight-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .risk-insight-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 13px 14px;
      background: #ffffff;
    }
    .risk-insight-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .risk-insight-card strong {
      display: block;
      margin-top: 4px;
      font-size: 21px;
      color: var(--ink);
    }
    .risk-insight-card em {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
    }
    .risk-explain-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .risk-explain-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: #fffaf7;
    }
    .risk-explain-item strong { margin-right: 8px; }
    .risk-explain-item span {
      color: var(--danger);
      font-size: 12px;
      font-weight: 800;
    }
    .risk-explain-item p {
      margin: 6px 0 0;
      color: #475569;
      font-size: 13px;
    }
    .signal-detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .signal-detail-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #ffffff;
    }
    .signal-detail-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .signal-detail-head span {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .signal-detail-head strong { flex: 1; }
    .signal-detail-card p {
      margin: 0 0 10px;
      color: #475569;
      font-size: 13px;
    }
    .signal-detail-card dl {
      display: grid;
      gap: 7px;
      margin: 0;
    }
    .signal-detail-card dl div {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 8px;
      align-items: start;
    }
    .signal-detail-card dt {
      color: var(--muted);
      font-size: 12px;
    }
    .signal-detail-card dd {
      margin: 0;
      color: var(--ink);
      font-size: 12px;
    }
    .muted, footer { color: var(--muted); font-size: 13px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    footer { margin-top: 14px; padding: 0 4px; }

    /* ---- 新风险仪表盘 ---- */
    .risk-dashboard-shell {
      max-width: 940px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(420px, 1fr) 220px;
      gap: 26px;
      align-items: center;
    }
    .gauge-stage {
      display: grid;
      place-items: center;
    }
    .new-gauge-svg {
      width: 100%;
      max-width: 640px;
      height: auto;
      overflow: visible;
    }
    .gauge-tick {
      font-size: 16px;
      font-weight: 700;
      fill: #475569;
    }
    .gauge-label {
      font-size: 14px;
      font-weight: 700;
      fill: #667085;
    }
    .gauge-score-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px 18px 16px;
      background: #ffffff;
      box-shadow: 0 12px 32px rgba(23, 32, 51, 0.05);
    }
    .gauge-score-card span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    .gauge-score-card strong {
      display: block;
      margin-top: 4px;
      font-size: 58px;
      line-height: 1;
      font-weight: 900;
    }
    .gauge-score-card b {
      display: block;
      margin-top: 4px;
      font-size: 22px;
    }
    .gauge-score-card em {
      display: inline-block;
      margin-top: 12px;
      padding: 4px 10px;
      border-radius: 99px;
      background: #fff4e6;
      color: #d36b23;
      font-size: 13px;
      font-style: normal;
      font-weight: 800;
    }
    .gauge-score-card p {
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 12px;
    }
    .gauge-legend-pro {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-top: 2px;
      grid-column: 1 / -1;
    }
    .gauge-legend-item {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 13px;
      color: var(--ink);
    }
    .gauge-legend-item span {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .gauge-legend-item strong {
      font-size: 13px;
      font-weight: 800;
      white-space: nowrap;
    }
    .gauge-legend-item em {
      color: var(--muted);
      font-style: normal;
      white-space: nowrap;
    }

    /* ---- 新六边形雷达 ---- */
    .radar-dashboard {
      display: grid;
      grid-template-columns: minmax(360px, 1fr) minmax(360px, 1fr);
      gap: 24px;
      align-items: center;
    }
    .radar-stage {
      min-height: 420px;
      display: grid;
      place-items: center;
    }
    .new-radar-svg {
      width: 100%;
      max-width: 520px;
      height: auto;
      flex-shrink: 0;
    }
    .radar-scale {
      font-size: 10px;
      fill: #94a3b8;
      font-weight: 600;
    }
    .radar-axis-label {
      font-size: 14px;
      fill: #172033;
      font-weight: 800;
    }
    .signal-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .signal-row {
      display: grid;
      grid-template-columns: 36px minmax(80px, 120px) 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 13px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      box-shadow: 0 8px 22px rgba(23, 32, 51, 0.04);
    }
    .signal-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: white;
      font-weight: 800;
      font-size: 13px;
    }
    .signal-0 { background: #2563eb; }
    .signal-1 { background: #7c3aed; }
    .signal-2 { background: #f97316; }
    .signal-3 { background: #0f766e; }
    .signal-4 { background: #ef4444; }
    .signal-5 { background: #64748b; }
    .signal-row strong { font-size: 14px; }
    .signal-row em {
      color: var(--muted);
      font-size: 13px;
      font-style: normal;
    }
    .signal-row b {
      padding: 4px 12px;
      border-radius: 99px;
      font-size: 12px;
      white-space: nowrap;
    }
    .signal-row b.bull { background: #e7f8ee; color: #16794c; }
    .signal-row b.bear { background: #fdeaea; color: #c2412d; }
    .signal-row b.watch { background: #fff4db; color: #b7791f; }
    .signal-row b.neutral { background: #f1f5f9; color: #667085; }

    /* ---- 操作建议决策卡 ---- */
    .decision-card {
      display: grid;
      grid-template-columns: 1fr auto 1fr auto 1fr;
      align-items: center;
      gap: 0;
      background: #f8fafc;
      border-radius: 12px;
      padding: 20px 16px;
      border: 1px solid var(--line);
    }
    .dc-col {
      text-align: center;
      padding: 8px 12px;
    }
    .dc-loss { border-right: none; }
    .dc-target { border-left: none; }
    .dc-current { padding: 8px 20px; }
    .dc-divider {
      width: 1px;
      height: 60px;
      background: var(--line);
    }
    .dc-label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    .dc-price { display: block; font-size: 20px; font-weight: 800; }
    .dc-price-main { font-size: 26px; color: var(--accent); }
    .dc-note { display: block; font-size: 11px; color: var(--muted); margin-top: 2px; }
    .dc-loss .dc-price { color: var(--danger); }
    .dc-target .dc-price { color: #16794c; }
    .dc-arrow { font-size: 14px; margin-bottom: 4px; }
    .dc-arrow-down { color: var(--danger); }
    .dc-arrow-up { color: #16794c; }
    .dc-action-badge {
      display: inline-block;
      padding: 3px 14px;
      border-radius: 99px;
      font-size: 13px;
      font-weight: 700;
      color: white;
      margin-bottom: 6px;
    }
    .dc-action-badge.healthy { background: #16794c; }
    .dc-action-badge.watch { background: #d79b2b; }
    .dc-action-badge.caution { background: #d36b23; }
    .dc-disclaimer { margin-top: 12px; text-align: center; }

    /* ---- 信号雷达图 ---- */
    .radar-wrapper {
      display: flex;
      align-items: center;
      gap: 24px;
    }
    .radar-svg {
      width: 200px;
      height: 200px;
      flex-shrink: 0;
    }
    .radar-grid {
      fill: none;
      stroke: var(--line);
      stroke-width: 0.5;
    }
    .radar-axis {
      stroke: var(--line);
      stroke-width: 0.3;
    }
    .radar-value {
      fill: rgba(36, 84, 214, 0.15);
      stroke: #2454d6;
      stroke-width: 1;
    }
    .radar-dot {
      fill: #2454d6;
    }
    .radar-label {
      font-size: 5px;
      fill: var(--muted);
      dominant-baseline: middle;
    }
    .radar-legend {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .rl-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }
    .rl-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* ---- 侧边导航 ---- */
    .side-nav {
      position: fixed;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 100;
    }
    .nav-item {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 2px 8px rgba(23,32,51,.06);
      font-size: 14px;
      text-decoration: none;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .nav-item:hover {
      transform: scale(1.12);
      box-shadow: 0 4px 12px rgba(23,32,51,.12);
      text-decoration: none;
    }

    /* ---- 品牌水印 ---- */
    main::after {
      content: "StockSight";
      position: fixed;
      bottom: 18px;
      right: 24px;
      font-size: 48px;
      font-weight: 900;
      color: rgba(23, 32, 51, 0.03);
      letter-spacing: -1px;
      pointer-events: none;
      z-index: 0;
    }
    footer {
      position: relative;
      z-index: 1;
    }
    .footer-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .footer-version { font-size: 11px; color: var(--muted); opacity: 0.6; }

    /* ---- 价格区间卡片 ---- */
    .price-range-card { padding: 8px 0; }
    .range-labels {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .range-track {
      position: relative;
      height: 28px;
      background: linear-gradient(90deg, #e74c3c 0%, #edf1f7 40%, #edf1f7 60%, #27ae60 100%);
      border-radius: 14px;
      margin: 0 4px;
    }
    .range-marker {
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      z-index: 2;
    }
    .marker-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,.2);
    }
    .range-marker.prev .marker-dot { background: #667085; }
    .range-marker.open .marker-dot { background: #2454d6; }
    .range-marker.current .marker-dot { background: var(--ink); width: 16px; height: 16px; border-width: 3px; }
    .marker-label {
      position: absolute;
      top: 22px;
      white-space: nowrap;
      font-size: 11px;
      color: var(--ink);
      font-weight: 600;
      background: white;
      padding: 1px 5px;
      border-radius: 4px;
      border: 1px solid var(--line);
    }
    .range-meta {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--muted);
      margin-top: 28px;
    }

    /* ---- 量价关系模块 ---- */
    .vp-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .vp-card {
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .vp-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }
    .vp-header h3 { margin: 0; font-size: 15px; }
    .vp-badge {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 99px;
      font-size: 12px;
      font-weight: 700;
      color: white;
    }
    .vp-badge.healthy { background: #16794c; }
    .vp-badge.caution { background: #d36b23; }
    .vp-badge.danger { background: #c2412d; }
    .vp-badge.neutral { background: #667085; }
    .vp-badge.watch { background: #d79b2b; }
    .vp-card p { margin: 0 0 12px; color: var(--muted); font-size: 13px; }
    .vp-bars { display: flex; flex-direction: column; gap: 8px; }
    .vp-bar-row {
      display: grid;
      grid-template-columns: 48px 1fr 48px;
      gap: 8px;
      align-items: center;
      font-size: 13px;
    }
    .vp-bar-row span { color: var(--muted); }
    .vp-bar-track {
      height: 8px;
      border-radius: 99px;
      background: #edf1f7;
      overflow: hidden;
    }
    .vp-bar-track i { display: block; height: 100%; border-radius: inherit; }
    .vp-bar-row strong { text-align: right; font-size: 13px; }
    .vp-dimension-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .vp-dim {
      background: white;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      text-align: center;
    }
    .dim-label { display: block; font-size: 11px; color: var(--muted); }
    .dim-value { display: block; font-size: 14px; margin-top: 2px; }

    /* ---- 资讯时间线 ---- */
    .timeline {
      position: relative;
      padding-left: 28px;
    }
    .timeline::before {
      content: "";
      position: absolute;
      left: 8px;
      top: 4px;
      bottom: 4px;
      width: 2px;
      background: var(--line);
      border-radius: 1px;
    }
    .timeline-item {
      position: relative;
      padding-bottom: 18px;
    }
    .timeline-item:last-child { padding-bottom: 0; }
    .timeline-dot {
      position: absolute;
      left: -24px;
      top: 4px;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--accent);
      border: 2px solid white;
      box-shadow: 0 0 0 2px var(--line);
    }
    .timeline-content h3 { margin: 0 0 4px; font-size: 14px; }
    .timeline-meta {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .timeline-meta span + span::before { content: "·"; margin: 0 4px; }
    .timeline-content p { margin: 4px 0 0; font-size: 13px; color: var(--muted); }

    /* ---- 数据完整性面板 ---- */
    .quality-panel { border-left: 4px solid var(--accent); }
    .qi-grid {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 20px;
      align-items: start;
    }
    .qi-ring { text-align: center; }
    .qi-ring-inner {
      width: 100px;
      aspect-ratio: 1;
      border-radius: 50%;
      margin: 0 auto 8px;
      display: grid;
      place-items: center;
      box-shadow: inset 0 0 0 12px rgba(255,255,255,.88);
    }
    .qi-ring-inner span { font-size: 20px; font-weight: 800; }
    .qi-items {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 6px;
    }
    .qi-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      border-radius: 6px;
      font-size: 13px;
      background: #f8fafc;
      border: 1px solid var(--line);
    }
    .qi-item.ok { border-color: #c6e4c6; }
    .qi-item.unavailable { border-color: #f5d6a8; }
    .qi-item.missing { border-color: #f0b8b8; }
    .qi-icon {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      font-size: 10px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
    }
    .qi-item.ok .qi-icon { background: #16794c; }
    .qi-item.unavailable .qi-icon { background: #d79b2b; }
    .qi-item.missing .qi-icon { background: #c2412d; }
    .qi-label { flex: 1; }
    .qi-status { color: var(--muted); font-size: 12px; }
    .qi-notes { grid-column: 1 / -1; margin-top: 8px; }
    .qi-notes p { margin: 4px 0; font-size: 13px; color: var(--muted); }

    /* ---- 响应式 ---- */
    @media (max-width: 820px) {
      main { width: 100%; margin: 0; }
      header { border-radius: 0; animation: none; padding: 26px 18px; }
      h1 { font-size: 26px; }
      .metric-grid, .chart-grid { grid-template-columns: 1fr; }
      .risk-insight-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .panel { border-radius: 0; margin-top: 12px; }
      .bar-row { grid-template-columns: 1fr; gap: 6px; }
      table { display: block; overflow-x: auto; }
      .vp-grid { grid-template-columns: 1fr; }
      .qi-grid { grid-template-columns: 1fr; }
      .qi-ring-inner { margin: 0 auto; }
      .side-nav { display: none; }
      .decision-card { grid-template-columns: 1fr; gap: 8px; }
      .dc-divider { width: 60px; height: 1px; margin: 0 auto; }
      .radar-dashboard { grid-template-columns: 1fr; }
      .radar-stage { min-height: auto; }
      .signal-row { grid-template-columns: 32px 1fr; }
      .signal-row em, .signal-row b { grid-column: 2; }
      .risk-dashboard-shell { grid-template-columns: 1fr; }
      .gauge-legend-pro { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    /* ---- 打印样式 ---- */
    @page {
      size: A4;
      margin: 10mm;
    }
    @media print {
      html, body {
        width: auto;
        min-width: 0;
        background: white;
        color: #172033;
        font-size: 10pt;
        line-height: 1.42;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      * {
        animation: none !important;
        transition: none !important;
        box-shadow: none !important;
        text-shadow: none !important;
      }
      main {
        width: 190mm;
        max-width: 190mm;
        margin: 0 auto;
      }
      main::after,
      .side-nav {
        display: none !important;
      }
      header {
        background: #172033 !important;
        border-radius: 0;
        padding: 14mm 10mm 10mm;
        break-inside: avoid;
        page-break-inside: avoid;
      }
      h1 { font-size: 22pt; }
      h2 { font-size: 15pt; margin-bottom: 8mm; }
      h3 { font-size: 11pt; }
      .panel {
        margin-top: 8mm;
        padding: 8mm;
        border: 1px solid #d8e0ec;
        border-radius: 0;
        break-inside: avoid;
        page-break-inside: avoid;
      }
      .metric-grid {
        grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
        gap: 4mm;
      }
      .metric,
      .chart-card,
      .risk-card,
      .vp-card,
      .risk-insight-card,
      .signal-detail-card,
      .signal-row,
      .qi-item {
        border: 1px solid #d8e0ec;
        background: #fff;
      }
      .chart-grid,
      .chart-grid.enriched {
        grid-template-columns: 42mm 1fr !important;
        gap: 6mm;
      }
      .risk-dashboard-shell {
        grid-template-columns: 1fr 44mm !important;
        gap: 6mm;
        max-width: none;
      }
      .new-gauge-svg {
        max-width: 118mm;
        width: 118mm;
      }
      .gauge-score-card {
        padding: 5mm;
      }
      .gauge-score-card strong {
        font-size: 32pt;
      }
      .gauge-score-card b {
        font-size: 13pt;
      }
      .gauge-legend-pro {
        grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
        gap: 3mm;
      }
      .gauge-legend-item {
        font-size: 8pt;
      }
      .radar-dashboard {
        grid-template-columns: 78mm 1fr !important;
        gap: 8mm;
        align-items: center;
      }
      .radar-stage {
        min-height: 0;
      }
      .new-radar-svg {
        width: 78mm;
        max-width: 78mm;
      }
      .signal-row {
        grid-template-columns: 8mm 24mm 1fr 16mm !important;
        gap: 3mm;
        padding: 3mm;
      }
      .signal-row em,
      .signal-row b {
        grid-column: auto !important;
      }
      .risk-insight-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
        gap: 3mm;
      }
      .signal-detail-grid,
      .risk-explain-list,
      .risk-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 4mm;
      }
      .vp-grid,
      .qi-grid {
        grid-template-columns: 1fr 1fr !important;
        gap: 5mm;
      }
      .decision-card {
        grid-template-columns: 1fr 1px 1fr 1px 1fr !important;
      }
      .dc-divider {
        width: 1px !important;
        height: 20mm !important;
      }
      table {
        page-break-inside: auto;
        font-size: 9pt;
      }
      tr { page-break-inside: avoid; }
      .bar-track { background: #edf1f7; }
      th { background: #f0f4fa; }
      .empty-state { background: #f8fafc; }
      a { color: #1a1a1a; text-decoration: underline; }
      footer { margin-top: 8px; }
    }
    """


# =============================================================================
# 主渲染入口
# =============================================================================

def render_html_report(data: ReportData, mode: str = "detailed") -> str:
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

    header_gradient = HEADER_GRADIENTS.get(top_level, HEADER_GRADIENTS[0])

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
            '<section class="panel" id="core">'
            "<h2>核心指标</h2>"
            '<div class="metric-grid">'
            + _metric_card("当前价", _html(format_price(first_stock.current_price, first_stock.market)))
            + _metric_card_heat("涨跌幅", f"{_html(format_change_plain(first_stock.change_percent))} {change_emoji(first_stock.change_percent)}", first_stock.change_percent)
            + _metric_card("量比", _html(format_volume_ratio(first_stock.volume_ratio)))
            + _metric_card("换手率", _html(format_turnover(first_stock.turnover_rate)))
            + _metric_card("成交额", _html(format_amount(first_stock.amount, first_stock.market)))
            + "</div>"
            f"<p class=\"muted\">成交量：{_html(format_volume(first_stock.volume, first_stock.market))}"
            f" · 市场标签：{_html(market_tag(first_stock.market) or '—')}</p>"
            "</section>"
        )

    price_range_section = _price_range_html(first_stock)
    volume_price_section = _volume_price_html(first_stock, visible_signals)

    detailed_only = ""
    if selected_mode == "detailed":
        detailed_only = (
            _risk_gauge_html(top_level, visible_signals)
            + _radar_html(visible_signals, first_stock)
            + _decision_card_html(first_stock, visible_signals)
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
        + _nav_html()
        + f'<header style="background: {header_gradient};">'
        f"<h1>{EmojiMap.ANALYSIS} {_html(title)}</h1>"
        f'<p class="summary">{EmojiMap.REPORT} {_html(subtitle)}</p>'
        '<div class="metric-grid">'
        + "".join(metric_cards)
        + "</div>"
        "</header>"
        + price_panel
        + price_range_section
        + volume_price_section
        + detailed_only
        + _risk_distribution_html(visible_signals)
        + _signal_composition_html(visible_signals)
        + _quality_html(visible_stocks)
        + _stock_table_html(visible_stocks, visible_signals)
        + _risk_notes_html(visible_signals)
        + _news_html(data)
        + f'<footer>'
        f'<div class="footer-row">'
        f'<span>{EmojiMap.DATA_SOURCE} 数据来源：{_html(data.data_source)} | {EmojiMap.CLOCK} {_html(data.timestamp)}</span>'
        f'<span class="footer-version">StockSight v{VERSION}</span>'
        f'</div>'
        f'<div class="muted">技术指标参考，不构成投资建议。</div>'
        f'</footer>'
        "</main>"
        "</body>"
        "</html>"
    )
    return body
