# -*- coding: utf-8 -*-
import unittest

from core import HistoryBar, StockHistory
from core.analysis import (
    analyze_technical_indicators,
    compute_macd,
    compute_rsi,
    detect_macd_signals,
    detect_rsi_signals,
    technical_risk_signals,
)


def history_from_closes(closes):
    return StockHistory(
        code="TEST",
        bars=[
            HistoryBar(
                date=f"2026-01-{index + 1:02d}",
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000 + index,
            )
            for index, close in enumerate(closes)
        ],
    )


class TechnicalAnalysisTests(unittest.TestCase):
    def test_compute_macd_returns_series_for_enough_history(self):
        history = history_from_closes([100 + index * 0.5 for index in range(60)])

        macd = compute_macd(history)

        self.assertEqual(len(macd.dif), 60)
        self.assertEqual(len(macd.dea), 60)
        self.assertEqual(len(macd.macd), 60)
        self.assertEqual(macd.dates[-1], "2026-01-60")

    def test_detect_macd_signals_finds_death_cross(self):
        history = history_from_closes(
            [100 + index * 0.8 for index in range(45)] + [136 - index * 1.2 for index in range(20)]
        )

        signals = detect_macd_signals(compute_macd(history), lookback=20)

        self.assertTrue(any(signal.signal_type == "death_cross" for signal in signals))

    def test_rsi_overbought_and_oversold_levels(self):
        overbought = compute_rsi(history_from_closes([100 + index for index in range(35)]))
        oversold = compute_rsi(history_from_closes([140 - index for index in range(35)]))

        overbought_signals = detect_rsi_signals(overbought)
        oversold_signals = detect_rsi_signals(oversold)

        self.assertEqual(overbought_signals[0].level, 3)
        self.assertEqual(overbought_signals[0].signal_type, "overbought_extreme")
        self.assertEqual(oversold_signals[0].level, 2)
        self.assertEqual(oversold_signals[0].signal_type, "oversold_extreme")

    def test_analyze_handles_insufficient_history(self):
        analysis = analyze_technical_indicators(history_from_closes([1, 2, 3]))

        self.assertEqual(analysis.macd.dates, [])
        self.assertIsNone(analysis.rsi.latest)
        self.assertTrue(analysis.notes)

    def test_technical_risk_signals_keeps_bullish_auxiliary_out_of_risk(self):
        analysis = analyze_technical_indicators(history_from_closes([100 + index for index in range(35)]))
        risks = technical_risk_signals(analysis, "TEST")

        self.assertTrue(risks)
        self.assertTrue(all(signal.stock_code == "TEST" for signal in risks))


if __name__ == "__main__":
    unittest.main()
