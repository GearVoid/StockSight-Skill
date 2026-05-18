# -*- coding: utf-8 -*-
"""Chart-like HTML sections for StockSight reports."""

from typing import Dict, List, Sequence, Tuple
import math

from core import RiskSignal, StockData
from .base import (
    fmt_signal_level,
    format_change_plain,
    format_price,
    format_turnover,
    format_volume_ratio,
    render_count_bar,
    render_signal_bar,
    risk_level_counts,
    risk_type_counts,
    signal_level_label,
)
from .html_utils import (
    LEVEL_COLORS,
    TYPE_COLORS,
    _calculate_risk_score,
    _get_risk_status,
    _html,
    _level_pie_gradient,
    _pie_gradient,
)

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
