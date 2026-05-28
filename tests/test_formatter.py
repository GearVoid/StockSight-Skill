# -*- coding: utf-8 -*-
import unittest

from core import BOLLResult, KDJResult, MACDResult, NewsItem, RSIResult, RiskSignal, TechnicalAnalysis, TechnicalSignal
from formatter import (
    render_detailed_report,
    render_html_report,
    render_standard_report,
    validate_report,
)
from formatter.html_utils import _calculate_risk_score, calculate_dual_risk_score

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
        data = sample_report(source_notes=["实时行情：unit", "历史行情：unit-history（80条）"])
        report = render_detailed_report(data)
        result = validate_report(report, data)

        self.assertTrue(result.passed, result.errors)
        self.assertIn("<details>", report)
        self.assertIn("技术指标辅助", report)
        self.assertIn("最终判断", report)
        self.assertIn("数据可信度", report)
        self.assertIn("报告口径", report)
        self.assertIn("数据来源链", report)
        self.assertIn("历史行情：unit-history", report)
        self.assertIn("使用 Snapshot", report)
        self.assertIn("突破确认", report)
        self.assertIn("确认条件", report)
        self.assertIn("失效条件", report)

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
        self.assertIn("StockSight v0.3.1", html)
        self.assertIn("异动强度", html)
        self.assertIn("下行风险", html)
        self.assertIn("异动强度拆解", html)
        self.assertIn("价格波动", html)
        self.assertIn("突破确认", html)
        self.assertIn("确认条件", html)

    def test_news_context_splits_hard_info_and_market_news(self):
        data = sample_report(news=[
            NewsItem(
                title="Sample 年度报告公告",
                source="东方财富公告",
                url="https://data.eastmoney.com/notices/detail/600001/a.html",
                published_at="2026-05-18",
                snippet="[财报] 年度报告摘要",
            ),
            NewsItem(
                title="Sample 股价异动",
                source="财经媒体",
                url="https://example.com/news",
                published_at="2026-05-18",
                snippet="[新闻] 市场关注度升温",
            ),
        ])

        markdown = render_detailed_report(data)
        html = render_html_report(data)

        self.assertIn("公司公告与硬信息", markdown)
        self.assertIn("市场资讯与舆情", markdown)
        self.assertIn("公司公告与硬信息", html)
        self.assertIn("市场资讯与舆情", html)

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
        self.assertIn("异动强度拆解", markdown)
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
            RiskSignal("TEST", "价格异动", 3, 9.8, "%", "跌停 price limit"),
            RiskSignal("TEST", "量比偏离", 3, 4.5, "x", "volume spike"),
            RiskSignal("TEST", "换手率异常", 2, 18.0, "%", "turnover spike"),
        ]

        self.assertGreater(_calculate_risk_score(market), _calculate_risk_score(technical))
        self.assertGreaterEqual(_calculate_risk_score(market), 80)

    def test_market_warnings_without_danger_are_capped_below_high_risk(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 2, 10.0, "%", "limit up watch"),
            RiskSignal("TEST", "RSI技术信号", 2, 73.0, "", "RSI overbought"),
            RiskSignal("TEST", "KDJ技术信号", 2, 0.0, "", "KDJ death cross"),
            RiskSignal("TEST", "BOLL技术信号", 1, 0.0, "", "near upper band"),
        ]

        self.assertLess(_calculate_risk_score(signals), 75)

    def test_limit_up_anomaly_can_be_high_while_downside_risk_is_capped(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 2, 10.0, "%", "涨幅绝对值10.0%，上涨方向按强异动观察"),
            RiskSignal("TEST", "量比偏离", 2, 2.4, "x", "量比放大但未到极端"),
        ]

        dual = calculate_dual_risk_score(signals)

        self.assertGreaterEqual(dual.anomaly_score, 60)
        self.assertLess(dual.risk_score, 70)

    def test_limit_down_keeps_higher_downside_risk(self):
        signals = [
            RiskSignal("TEST", "超额收益异动", 3, 10.0, "%", "跌停，下跌风险扩大"),
            RiskSignal("TEST", "量比偏离", 3, 4.1, "x", "放量下跌"),
        ]

        dual = calculate_dual_risk_score(signals)

        self.assertGreaterEqual(dual.risk_score, 75)


if __name__ == "__main__":
    unittest.main()
