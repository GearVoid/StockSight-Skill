"""Small HTML rendering utilities for StockSight reports."""

from html import escape
from typing import Dict, List, Sequence, Tuple

from core import ReportData, RiskSignal, StockData

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
