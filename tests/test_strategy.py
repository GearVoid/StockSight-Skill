# -*- coding: utf-8 -*-
import unittest

from core import (
    BOLLResult,
    KDJResult,
    MACDResult,
    NewsItem,
    RSIResult,
    TechnicalAnalysis,
    TrendSummary,
    evaluate_strategy_action,
)

from tests.fixtures import sample_signal, sample_stock


def technical_context(
    *,
    macd_alignment="neutral",
    histogram="flat",
    rsi=55.0,
    rsi_trend="neutral",
    divergence="",
    boll_latest=None,
    kdj_j=50.0,
):
    return TechnicalAnalysis(
        macd=MACDResult(dif=[0.1, 0.2, 0.3], dea=[0.0, 0.1, 0.2], macd=[0.1, 0.2, 0.3]),
        rsi=RSIResult(values=[rsi], dates=["2026-05-20"]),
        boll=BOLLResult(
            upper=[boll_latest[0]] if boll_latest else [],
            middle=[boll_latest[1]] if boll_latest else [],
            lower=[boll_latest[2]] if boll_latest else [],
        ),
        kdj=KDJResult(k=[50.0], d=[45.0], j=[kdj_j]),
        trend=TrendSummary(
            macd_alignment=macd_alignment,
            macd_alignment_desc=f"MACD {macd_alignment}",
            macd_histogram_trend=histogram,
            rsi_trend=rsi_trend,
            rsi_trend_desc=f"RSI {rsi_trend}",
            divergence=divergence,
            divergence_desc="价格创新高但 MACD 未确认，顶背离风险" if divergence else "",
        ),
    )


class StrategyTests(unittest.TestCase):
    def test_hard_news_risk_overrides_technical_setup(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=3.2, volume_ratio=2.2)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="bullish", rsi=58.0),
            [NewsItem(title="柘中股份收到监管问询函", source="公告", published_at="2026-05-18")],
        )

        self.assertEqual(decision.action, "风险规避")
        self.assertEqual(decision.tone, "danger")

    def test_old_hard_news_does_not_override_current_technical_setup(self):
        stock = sample_stock(
            code="002346",
            name="柘中股份",
            change_percent=1.2,
            volume_ratio=1.2,
            turnover_rate=3.0,
            timestamp="2026-05-28 10:00:00",
        )
        old_news = NewsItem(
            title="柘中股份重大事项停牌进展公告",
            source="巨潮资讯",
            published_at="2015-04-29",
            snippet="[风险提示] 重大事项存在不确定性，提醒投资者注意风险。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [old_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_unrelated_hard_news_does_not_cross_contaminate_strategy(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=1.2, volume_ratio=1.2)
        unrelated_news = NewsItem(
            title="其他股份收到监管处罚",
            source="公告",
            published_at="2026-05-18",
            snippet="[风险提示] 其他股份存在退市风险。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [unrelated_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_undated_hard_news_is_report_context_only(self):
        stock = sample_stock(code="002346", name="柘中股份", change_percent=1.2, volume_ratio=1.2)
        undated_news = NewsItem(
            title="柘中股份风险提示公告",
            source="搜索结果",
            snippet="[风险提示] 未给出发布时间的历史搜索结果。",
        )

        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
            [undated_news],
        )

        self.assertEqual(decision.action, "趋势持有")

    def test_volume_breakout_with_bullish_macd_needs_confirmation(self):
        stock = sample_stock(change_percent=3.4, volume_ratio=2.1, turnover_rate=6.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="量比偏离", level=2, description="量比放大")],
            technical_context(macd_alignment="bullish", rsi=62.0),
        )

        self.assertEqual(decision.action, "突破确认")
        self.assertIn("放量上涨", decision.summary)

    def test_bullish_trend_without_major_risk_is_trend_hold(self):
        stock = sample_stock(change_percent=1.2, volume_ratio=1.2, turnover_rate=3.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=1, description="偏热但未超买")],
            technical_context(macd_alignment="bullish", rsi=56.0),
        )

        self.assertEqual(decision.action, "趋势持有")
        self.assertEqual(decision.tone, "healthy")

    def test_overheated_signal_cools_down_before_breakout(self):
        stock = sample_stock(change_percent=4.0, volume_ratio=2.2, turnover_rate=12.0)
        decision = evaluate_strategy_action(
            stock,
            [sample_signal(risk_type="RSI技术信号", level=2, description="RSI 超买")],
            technical_context(macd_alignment="bullish", rsi=78.0),
        )

        self.assertEqual(decision.action, "高位降温")
        self.assertEqual(decision.tone, "warning")

    def test_oversold_without_downside_event_is_low_repair(self):
        stock = sample_stock(change_percent=-0.8, volume_ratio=0.9, turnover_rate=2.0)
        decision = evaluate_strategy_action(
            stock,
            [],
            technical_context(macd_alignment="neutral", rsi=28.0, rsi_trend="oversold_bounce"),
        )

        self.assertEqual(decision.action, "低位修复")
        self.assertIn("修复", decision.summary)


if __name__ == "__main__":
    unittest.main()
