# -*- coding: utf-8 -*-
import unittest

from core import BOLLResult, KDJResult, MACDResult, RSIResult, RiskSignal, TechnicalAnalysis, TechnicalSignal
from formatter import (
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)
from formatter.html_utils import _calculate_risk_score

from tests.fixtures import sample_report


class FormatterTests(unittest.TestCase):
    def test_standard_report_validates(self):
        data = sample_report()
        report = render_standard_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<kbd>", report)
        self.assertIn("▰", report)
        self.assertIn("报告口径", report)
        self.assertIn("行情时间", report)

    def test_detailed_report_validates(self):
        data = sample_report()
        report = render_detailed_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<details>", report)
        self.assertIn("技术指标辅助", report)
        self.assertIn("最终判断", report)
        self.assertIn("数据可信度", report)
        self.assertIn("报告口径", report)
        self.assertIn("使用 Snapshot", report)

    def test_html_report_contains_split_sections(self):
        html = render_html_report(sample_report())

        self.assertIn("<!doctype html>", html)
        self.assertIn("<style>", html)
        self.assertIn("risk-dashboard-shell", html)
        self.assertIn("new-radar-svg", html)
        self.assertIn('id="judgment"', html)
        self.assertIn("数据可信度", html)
        self.assertIn("行情时间", html)
        self.assertIn("Snapshot", html)
        self.assertIn("StockSight v2.0", html)

    def test_html_report_without_signals_does_not_create_fake_pie(self):
        html = render_html_report(sample_report(signal=None, news=[]))

        self.assertIn("<!doctype html>", html)
        self.assertIn("empty-state", html)
        self.assertNotIn("Sample news", html)

    def test_technical_analysis_renders_in_markdown_and_html(self):
        technical = TechnicalAnalysis(
            macd=MACDResult(
                dif=[0.0, 0.1, 0.2],
                dea=[0.0, 0.12, 0.18],
                macd=[0.0, -0.04, 0.04],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
            ),
            rsi=RSIResult(
                values=[0.0, 65.0, 72.5],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=14,
            ),
            boll=BOLLResult(
                upper=[0.0, 110.0, 112.0],
                middle=[0.0, 100.0, 101.0],
                lower=[0.0, 90.0, 91.0],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=20,
            ),
            kdj=KDJResult(
                k=[0.0, 76.0, 82.0],
                d=[0.0, 72.0, 78.0],
                j=[0.0, 84.0, 90.0],
                dates=["2026-01-01", "2026-01-02", "2026-01-03"],
                period=9,
            ),
            signals=[
                TechnicalSignal(
                    indicator="RSI",
                    signal_type="overbought",
                    level=2,
                    direction="bearish",
                    date="2026-01-03",
                    value=72.5,
                    description="超买：RSI 高于 70，需警惕追高风险。",
                )
            ],
        )
        data = sample_report(technical=technical)

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("技术指标辅助", markdown)
        self.assertIn("RSI14", markdown)
        self.assertIn("BOLL20", markdown)
        self.assertIn("KDJ9", markdown)
        self.assertIn("RSI技术信号", html)
        self.assertIn("BOLL20", html)
        self.assertIn("KDJ9", html)
        self.assertIn("technical-grid", html)
        self.assertIn("rsi-track", html)

    def test_technical_only_risk_score_is_capped(self):
        signals = [
            RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought"),
            RiskSignal("AAPL", "MACD技术信号", 1, 0.0, "", "MACD helper"),
        ]

        self.assertLessEqual(_calculate_risk_score(signals), 60)

    def test_duplicate_technical_signals_have_diminishing_score(self):
        signals = [
            RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought"),
            RiskSignal("AAPL", "KDJ技术信号", 2, 0.0, "", "KDJ death cross"),
            RiskSignal("AAPL", "KDJ技术信号", 2, 82.1, "", "KDJ overbought"),
        ]

        self.assertLess(_calculate_risk_score(signals), 60)

    def test_market_risks_can_score_higher_than_technical_only(self):
        technical = [RiskSignal("AAPL", "RSI技术信号", 2, 72.1, "", "RSI overbought")]
        market = [
            RiskSignal("TEST", "价格异动", 3, 9.8, "%", "price limit"),
            RiskSignal("TEST", "量比偏离", 3, 4.5, "x", "volume spike"),
            RiskSignal("TEST", "换手率异常", 2, 18.0, "%", "turnover spike"),
        ]

        self.assertGreater(_calculate_risk_score(market), _calculate_risk_score(technical))
        self.assertGreaterEqual(_calculate_risk_score(market), 80)


if __name__ == "__main__":
    unittest.main()
