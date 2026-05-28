# -*- coding: utf-8 -*-
"""Rule-based strategy action layer.

This module converts quote anomalies and technical context into an explainable
report action. It is deliberately conservative: the action describes a setup to
track, not an order instruction.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .types import NewsItem, RiskSignal, StockData, TechnicalAnalysis


ACTION_RISK_AVOID = "风险规避"
ACTION_PULLBACK_WATCH = "回撤观察"
ACTION_COOLDOWN = "高位降温"
ACTION_BREAKOUT_CONFIRM = "突破确认"
ACTION_TREND_HOLD = "趋势持有"
ACTION_LOW_REPAIR = "低位修复"
ACTION_STABLE_TRACK = "平稳跟踪"


@dataclass(frozen=True)
class StrategyDecision:
    """Explainable strategy decision for report rendering."""

    action: str
    tone: str
    summary: str
    basis: List[str] = field(default_factory=list)
    confirmation: str = ""
    invalidation: str = ""
    risk_note: str = ""


def evaluate_strategy_action(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis] = None,
    news: Optional[Sequence[NewsItem]] = None,
) -> StrategyDecision:
    """Evaluate a report-level strategy action from market and technical data."""
    signals = list(signals or [])
    news = list(news or [])
    max_level = max((int(signal.level or 0) for signal in signals), default=0)
    text = _combined_text(signals, news)

    trend = getattr(technical, "trend", None) if technical else None
    macd_alignment = getattr(trend, "macd_alignment", "") or ""
    rsi_trend = getattr(trend, "rsi_trend", "") or ""
    divergence = getattr(trend, "divergence", "") or ""
    rsi_latest = getattr(getattr(technical, "rsi", None), "latest", None) if technical else None
    boll_latest = getattr(getattr(technical, "boll", None), "latest", None) if technical else None
    kdj_latest = getattr(getattr(technical, "kdj", None), "latest", None) if technical else None

    change = stock.change_percent
    vr = stock.volume_ratio
    tr = stock.turnover_rate
    price_position = _boll_position(stock.current_price, boll_latest)
    kdj_j = kdj_latest[2] if kdj_latest else None

    hard_risk = _has_hard_risk(text)
    downside = _has_downside_signal(text) or (change <= -3 and vr >= 1.5)
    overheated = (
        (rsi_latest is not None and rsi_latest >= 75)
        or divergence == "bearish"
        or (kdj_j is not None and kdj_j >= 100)
        or (price_position == "above_upper" and change > 0)
    )
    breakout = (
        change >= 2
        and vr >= 1.5
        and macd_alignment != "bearish"
        and not hard_risk
        and not downside
        and not overheated
        and (rsi_latest is None or 45 <= rsi_latest < 75)
    )
    trend_hold = (
        macd_alignment == "bullish"
        and not hard_risk
        and not downside
        and not overheated
        and max_level <= 1
        and (rsi_latest is None or 40 <= rsi_latest < 70)
    )
    low_repair = (
        not hard_risk
        and not downside
        and (
            (rsi_latest is not None and rsi_latest <= 35)
            or rsi_trend == "oversold_bounce"
            or price_position == "near_lower"
            or (kdj_j is not None and kdj_j <= 20)
        )
    )

    basis = _basis(stock, signals, technical)
    if hard_risk:
        return StrategyDecision(
            action=ACTION_RISK_AVOID,
            tone="danger",
            summary="硬信息或事件风险优先，暂不宜用普通技术反弹逻辑解释。",
            basis=basis,
            confirmation="先确认公告、监管、业绩或股东变动的影响是否消化。",
            invalidation="只有事件风险解除且量价重新稳定，风险优先级才会下降。",
            risk_note="事件风险可能覆盖技术指标信号。",
        )

    if downside and (max_level >= 3 or macd_alignment == "bearish" or change <= -5):
        return StrategyDecision(
            action=ACTION_RISK_AVOID,
            tone="danger",
            summary="下行信号与高等级异动共振，风险控制优先。",
            basis=basis,
            confirmation="观察是否跌破近期支撑，并确认放量下跌是否延续。",
            invalidation="若缩量企稳且 MACD 空头收敛，风险可降为回撤观察。",
            risk_note="放量下跌或破位信号不适合按低位修复处理。",
        )

    if downside:
        return StrategyDecision(
            action=ACTION_PULLBACK_WATCH,
            tone="warning",
            summary="价格方向偏弱，优先等待支撑和量能企稳。",
            basis=basis,
            confirmation="确认回撤是否缩量，并观察 MACD/RSI 是否停止走弱。",
            invalidation="若继续放量下跌或跌破关键区间，升级为风险规避。",
            risk_note="回撤阶段不宜只看单个超卖信号。",
        )

    if overheated:
        return StrategyDecision(
            action=ACTION_COOLDOWN,
            tone="warning",
            summary="短线动能偏热，降低追高冲动，等待指标降温或回踩确认。",
            basis=basis,
            confirmation="确认 RSI/KDJ 是否回落，价格是否仍能站稳强势区间。",
            invalidation="若高换手叠加 MACD 柱收敛或顶背离扩大，过热风险上升。",
            risk_note="强趋势可延续，但高位拥挤会放大回撤波动。",
        )

    if breakout:
        return StrategyDecision(
            action=ACTION_BREAKOUT_CONFIRM,
            tone="watch",
            summary="放量上涨叠加多头动能，出现突破确认型机会。",
            basis=basis,
            confirmation="确认后续是否继续放量，并站稳当前价格区间。",
            invalidation="若量能回落且 MACD 柱体收敛，突破有效性下降。",
            risk_note="突破信号需要后续收盘位置和量能共同确认。",
        )

    if trend_hold:
        return StrategyDecision(
            action=ACTION_TREND_HOLD,
            tone="healthy",
            summary="趋势结构偏多，适合沿既定趋势继续跟踪。",
            basis=basis,
            confirmation="确认上涨量能是否温和延续，避免量价背离。",
            invalidation="若 MACD 转为空头或 RSI 快速跌破中性区间，趋势持有条件失效。",
            risk_note="趋势持有仍需遵守既定止损和仓位纪律。",
        )

    if low_repair:
        return StrategyDecision(
            action=ACTION_LOW_REPAIR,
            tone="watch",
            summary="低位或超卖修复迹象出现，但需要放量和趋势拐点确认。",
            basis=basis,
            confirmation="确认 RSI/KDJ 是否继续回升，并观察价格能否收回关键均衡区。",
            invalidation="若反弹无量或继续跌破下轨，修复假设失效。",
            risk_note="低位修复属于观察型动作，不等同于趋势反转。",
        )

    return StrategyDecision(
        action=ACTION_STABLE_TRACK,
        tone="healthy",
        summary="量价和技术结构暂未出现强方向信号，按既定策略跟踪。",
        basis=basis,
        confirmation="继续观察成交量、价格区间和 MACD/RSI/BOLL/KDJ 是否同步转强或转弱。",
        invalidation="若出现放量破位、极端换手或硬风险信息，平稳跟踪条件失效。",
        risk_note="数据不足时应降低策略判断权重。",
    )


def _basis(
    stock: StockData,
    signals: Sequence[RiskSignal],
    technical: Optional[TechnicalAnalysis],
) -> List[str]:
    items = [
        f"涨跌幅 {stock.change_percent:+.2f}%",
        f"量比 {stock.volume_ratio:.2f}" if stock.volume_ratio > 0 else "量比缺失",
        f"换手率 {stock.turnover_rate:.1f}%" if stock.turnover_rate > 0 else "换手率缺失",
    ]
    if signals:
        top = max(signals, key=lambda signal: int(signal.level or 0))
        items.append(f"最高异动 {top.risk_type} L{top.level}")

    trend = getattr(technical, "trend", None) if technical else None
    if trend and getattr(trend, "macd_alignment_desc", ""):
        items.append(trend.macd_alignment_desc)
    rsi_latest = getattr(getattr(technical, "rsi", None), "latest", None) if technical else None
    if rsi_latest is not None:
        items.append(f"RSI {rsi_latest:.1f}")
    if trend and getattr(trend, "divergence_desc", ""):
        items.append(trend.divergence_desc)
    return items[:6]


def _combined_text(signals: Sequence[RiskSignal], news: Sequence[NewsItem]) -> str:
    signal_text = " ".join(
        f"{signal.risk_type} {signal.description}" for signal in signals
    )
    news_text = " ".join(
        f"{item.title} {item.source} {item.snippet}" for item in news
    )
    return f"{signal_text} {news_text}"


def _has_hard_risk(text: str) -> bool:
    keywords = (
        "风险提示",
        "退市",
        "监管",
        "处罚",
        "立案",
        "预亏",
        "业绩下修",
        "减持",
        "质押",
        "问询函",
    )
    return any(keyword in text for keyword in keywords)


def _has_downside_signal(text: str) -> bool:
    keywords = ("下跌", "跌停", "跑输", "走弱", "回撤", "破位", "顶背离", "死叉")
    return any(keyword in text for keyword in keywords)


def _boll_position(price: float, latest: Optional[tuple]) -> str:
    if not latest:
        return ""
    upper, middle, lower = latest
    if upper <= lower:
        return ""
    band = upper - lower
    if price >= upper:
        return "above_upper"
    if price >= upper - band * 0.15:
        return "near_upper"
    if price <= lower:
        return "below_lower"
    if price <= lower + band * 0.15:
        return "near_lower"
    if price >= middle:
        return "upper_half"
    return "lower_half"
