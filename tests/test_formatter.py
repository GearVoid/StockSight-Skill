# -*- coding: utf-8 -*-
import unittest

from core import MACDResult, RSIResult, TechnicalAnalysis, TechnicalSignal
from formatter import (
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)

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
        self.assertIn("RSI技术信号", html)
        self.assertIn("technical-grid", html)
        self.assertIn("rsi-track", html)


if __name__ == "__main__":
    unittest.main()
