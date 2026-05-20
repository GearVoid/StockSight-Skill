# -*- coding: utf-8 -*-
"""Technical analysis indicators for StockSight."""

from __future__ import annotations

from typing import List, Sequence

from .types import (
    MACDResult,
    RSIResult,
    RiskSignal,
    StockHistory,
    TechnicalAnalysis,
    TechnicalSignal,
)


def _ema(values: Sequence[float], period: int) -> List[float]:
    """Compute exponential moving average with an SMA seed."""
    if period <= 0 or len(values) < period:
        return [0.0] * len(values)
    multiplier = 2.0 / (period + 1)
    result = [0.0] * len(values)
    result[period - 1] = sum(values[:period]) / period
    for index in range(period, len(values)):
        result[index] = (values[index] - result[index - 1]) * multiplier + result[index - 1]
    return result


def compute_macd(history: StockHistory, fast: int = 12, slow: int = 26, signal: int = 9) -> MACDResult:
    """Calculate MACD from historical price bars."""
    if history is None or not history.bars or len(history.bars) < slow + signal - 1:
        return MACDResult()

    closes = [bar.close for bar in history.bars]
    dates = [bar.date for bar in history.bars]
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    dif = [0.0] * len(closes)
    for index in range(slow - 1, len(closes)):
        if ema_fast[index] and ema_slow[index]:
            dif[index] = ema_fast[index] - ema_slow[index]

    dea = _ema(dif, signal)
    dea_start = slow + signal - 2
    macd_hist = [0.0] * len(closes)
    for index in range(dea_start, len(closes)):
        macd_hist[index] = 2.0 * (dif[index] - dea[index])

    return MACDResult(
        dif=[round(value, 4) for value in dif],
        dea=[round(value, 4) for value in dea],
        macd=[round(value, 4) for value in macd_hist],
        dates=dates,
    )


def compute_rsi(history: StockHistory, period: int = 14) -> RSIResult:
    """Calculate RSI using Wilder smoothing."""
    if history is None or not history.bars or len(history.bars) <= period:
        return RSIResult(period=period)

    closes = [bar.close for bar in history.bars]
    dates = [bar.date for bar in history.bars]
    values = [0.0] * len(closes)
    gains: List[float] = []
    losses: List[float] = []

    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    values[period] = _rsi_from_averages(avg_gain, avg_loss)

    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        values[index] = _rsi_from_averages(avg_gain, avg_loss)

    return RSIResult(
        values=[round(value, 2) for value in values],
        dates=dates,
        period=period,
    )


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def detect_macd_signals(macd_result: MACDResult, lookback: int = 3) -> List[TechnicalSignal]:
    """Detect recent MACD golden/death crosses."""
    if not macd_result or len(macd_result.dif) < 3:
        return []

    dif = macd_result.dif
    dea = macd_result.dea
    dates = macd_result.dates
    start = max(1, len(dif) - max(1, lookback))
    signals: List[TechnicalSignal] = []

    for index in range(start, len(dif)):
        if dif[index] == 0 or dea[index] == 0 or dif[index - 1] == 0 or dea[index - 1] == 0:
            continue
        if dif[index - 1] <= dea[index - 1] and dif[index] > dea[index]:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal_type="golden_cross",
                level=0,
                direction="bullish",
                date=dates[index],
                value=dif[index] - dea[index],
                description="MACD 金叉：DIF 上穿 DEA，短线偏多。",
            ))
        elif dif[index - 1] >= dea[index - 1] and dif[index] < dea[index]:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal_type="death_cross",
                level=2,
                direction="bearish",
                date=dates[index],
                value=dif[index] - dea[index],
                description="MACD 死叉：DIF 下穿 DEA，短线转弱风险升高。",
            ))
    return signals


def detect_rsi_signals(rsi_result: RSIResult) -> List[TechnicalSignal]:
    """Detect RSI overbought/oversold states from the latest value."""
    latest = rsi_result.latest if rsi_result else None
    if latest is None or not rsi_result.dates:
        return []

    latest_date = rsi_result.dates[-1]
    if latest >= 80:
        return [_rsi_signal(latest_date, latest, 3, "overbought_extreme", "极度超买：RSI 高于 80，短线回撤风险较高。")]
    if latest >= 70:
        return [_rsi_signal(latest_date, latest, 2, "overbought", "超买：RSI 高于 70，需警惕追高风险。")]
    if latest >= 60:
        return [_rsi_signal(latest_date, latest, 1, "heated", "偏热：RSI 高于 60，动能偏强但需观察持续性。")]
    if latest <= 20:
        return [_rsi_signal(latest_date, latest, 2, "oversold_extreme", "极度超卖：RSI 低于 20，趋势压力仍需观察。")]
    if latest <= 30:
        return [_rsi_signal(latest_date, latest, 1, "oversold", "超卖观察：RSI 低于 30，可能出现修复需求。")]
    return []


def _rsi_signal(date: str, value: float, level: int, signal_type: str, description: str) -> TechnicalSignal:
    direction = "bullish" if "oversold" in signal_type else "bearish"
    return TechnicalSignal(
        indicator="RSI",
        signal_type=signal_type,
        level=level,
        direction=direction,
        date=date,
        value=round(value, 2),
        description=description,
    )


def analyze_technical_indicators(history: StockHistory) -> TechnicalAnalysis:
    """Compute MACD/RSI and summarize technical signals."""
    if history is None or not history.bars:
        return TechnicalAnalysis(notes=["历史数据不足，无法计算 MACD/RSI。"])

    macd = compute_macd(history)
    rsi = compute_rsi(history)
    signals = detect_macd_signals(macd, lookback=5) + detect_rsi_signals(rsi)
    notes: List[str] = []
    if not macd.dates:
        notes.append("MACD 历史数据不足。")
    if rsi.latest is None:
        notes.append("RSI 历史数据不足。")
    return TechnicalAnalysis(macd=macd, rsi=rsi, signals=signals, notes=notes)


def technical_risk_signals(analysis: TechnicalAnalysis, stock_code: str) -> List[RiskSignal]:
    """Convert risk-bearing technical signals into standard RiskSignal entries."""
    if not analysis or not analysis.signals:
        return []
    signals: List[RiskSignal] = []
    for item in analysis.signals:
        if item.level <= 0:
            continue
        signals.append(RiskSignal(
            stock_code=stock_code,
            risk_type=f"{item.indicator}技术信号",
            level=item.level,
            deviation_value=item.value,
            deviation_unit="" if item.indicator == "MACD" else "",
            description=item.description,
        ))
    return signals
