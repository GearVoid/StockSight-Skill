"""详细模式报告渲染

对标 VISUAL_SPECS.md Section 6.3（详细模式）和 EXAMPLES.md Example 2。

报告结构（固定顺序，单只股票）：
  1. H1: 🔍 深度分析标题
  2. 引用摘要
  3. H2: 💰 价格概览（2列表格）
  4. H2: 📊 量价指标（段落列表）
  5. H2: 🔍 异动分析（H3 子维度）
  6. H2: ⚠️ 风险提示
  7. H2: 🎯 操作建议（含止损/目标参考）
  8. H3: 关注维度汇总表
  9. 数据来源标注
"""

from typing import List, Optional

from core import RiskSignal, StockData, ReportData
from .base import (
    EmojiMap,
    change_emoji,
    fmt_signal_level,
    format_price,
    format_change_plain,
    format_volume,
    format_amount,
    format_volume_ratio,
    format_turnover,
    market_tag,
    render_badge,
    render_metric_strip,
    render_signal_bar,
    risk_level_symbol,
    render_table,
)


def _calc_amplitude(stock: StockData) -> float:
    """计算振幅（%）"""
    if stock.prev_close == 0:
        return 0.0
    return (stock.high - stock.low) / stock.prev_close * 100


def _calc_excess_return(stock: StockData) -> Optional[float]:
    """计算超额收益（无板块数据时返回 None）"""
    return None


def _stop_loss(price: float) -> float:
    """止损参考价（-5%）"""
    return round(price * 0.95, 2)


def _target_price(price: float) -> float:
    """目标参考价（+5.6%）"""
    return round(price * 1.056, 2)


def _format_signals_text(signals: List[RiskSignal], stock: StockData) -> str:
    """格式化异动分析段落"""
    parts = []
    for sig in signals:
        symbol = risk_level_symbol(sig.level)
        parts.append(f"### {sig.risk_type}（{symbol}）")
        parts.append(f"{sig.description}（偏离度 {sig.deviation_value:.1f}{sig.deviation_unit}）。")
        parts.append("")
    return "\n".join(parts)


def _risk_warnings(signals: List[RiskSignal]) -> str:
    """格式化风险提示"""
    lines = []
    for i, sig in enumerate(signals):
        symbol = risk_level_symbol(sig.level)
        lines.append(f"{symbol} {render_badge(sig.risk_type)} {render_signal_bar(sig.level)}")
        lines.append(f"{sig.description}（偏离度 {sig.deviation_value:.1f}{sig.deviation_unit}）。")
        lines.append("")
    return "\n".join(lines)


def _highest_risk(signals: List[RiskSignal]) -> str:
    """最高风险显示。"""
    max_level = max((sig.level for sig in signals), default=0)
    if max_level == 0:
        return f"{EmojiMap.OP_BUY} {render_badge('平稳')}"
    return f"{fmt_signal_level(max_level)} {render_signal_bar(max_level)}"


def _render_core_panel(stock: StockData, signals: List[RiskSignal]) -> str:
    """渲染详细报告核心看板。"""
    metrics = [
        ("当前价", format_price(stock.current_price, stock.market)),
        ("涨跌幅", f"{format_change_plain(stock.change_percent)} {change_emoji(stock.change_percent)}"),
        ("量比", format_volume_ratio(stock.volume_ratio)),
        ("换手率", format_turnover(stock.turnover_rate)),
        ("最高风险", _highest_risk(signals)),
    ]
    return render_metric_strip(metrics)


def _render_news_details(data: ReportData) -> str:
    """渲染可折叠新闻区块。"""
    if not data.news:
        return ""
    lines = [
        "<details>",
        f"<summary>{EmojiMap.NEWS} 相关资讯</summary>",
        "",
    ]
    for item in data.news[:5]:
        title = item.title or "—"
        source = item.source or "—"
        time = f"（{item.published_at}）" if item.published_at else ""
        lines.append(f"[{source}] {title}{time}")
        if item.snippet:
            lines.append(f"  {EmojiMap.NOTE} {item.snippet}")
        lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def _dimension_table(stock: StockData, signals: List[RiskSignal]) -> str:
    """渲染关注维度汇总表（3列）"""
    # 量价关系
    if stock.change_percent > 2 and stock.volume_ratio > 1.5:
        vol_price = f"{EmojiMap.OP_BUY} 健康"
        vol_price_note = "价升量增，看多信号"
    elif stock.change_percent < -2 and stock.volume_ratio > 1.5:
        vol_price = f"{EmojiMap.OP_SELL} 谨慎"
        vol_price_note = "价跌量增，需关注"
    else:
        vol_price = f"{EmojiMap.OP_HOLD} 平稳"
        vol_price_note = "量价配合正常"

    # 资金活跃度
    max_level = max((s.level for s in signals), default=0)
    if max_level >= 3:
        active = f"{risk_level_symbol(3)} 危险"
        active_note = "多项指标异常，需重点监控"
    elif max_level >= 2:
        active = f"{risk_level_symbol(2)} 关注"
        active_note = f"量比/换手率异常，需确认持续性 {render_signal_bar(2)}"
    elif max_level >= 1:
        active = f"{risk_level_symbol(1)} 留意"
        active_note = "轻度偏离，常规关注"
    else:
        active = f"{EmojiMap.OP_BUY} 正常"
        active_note = "各项指标正常"

    headers = ["维度", "状态", "说明"]
    rows = [
        ["量价关系", vol_price, vol_price_note],
        ["资金活跃度", active, active_note],
    ]
    return render_table(headers, rows)


def render_detailed_report(data: ReportData) -> str:
    """渲染详细模式报告（单只股票深度分析）
    
    取 signals 中等级最高的股票进行分析；无信号时取列表第一只。
    
    Args:
        data: 报告数据包
        
    Returns:
        格式化后的 Markdown 报告文本
    """
    # 选择分析目标
    target_stock: Optional[StockData] = None
    target_signals: List[RiskSignal] = []

    if data.signals:
        # 按等级降序取第一只
        top_signal = max(data.signals, key=lambda s: s.level)
        target_stock = next(
            (s for s in data.stocks if s.code == top_signal.stock_code), None
        )
        target_signals = [s for s in data.signals if s.stock_code == top_signal.stock_code]
    elif data.stocks:
        target_stock = data.stocks[0]

    if target_stock is None:
        return f"{EmojiMap.REPORT} 无可用数据生成深度报告"

    stock = target_stock
    signals = target_signals
    stock_label = f"{stock.name} ({stock.code})"
    amplitude = _calc_amplitude(stock)

    parts = []

    # 1. H1: 标题
    parts.append(f"# {EmojiMap.ANALYSIS} {stock_label} 深度分析报告")
    parts.append("")

    # 2. 摘要行（一句，不重复）
    emoji = change_emoji(stock.change_percent)
    summary_text = (
        f"> {EmojiMap.REPORT} 一句话总结："
        f"{f'`[{market_tag(stock.market)}]` ' if market_tag(stock.market) else ''}"
        f"{stock.name}今日收{format_price(stock.current_price, stock.market)}，"
        f"涨跌幅{format_change_plain(stock.change_percent)} {emoji}"
    )
    if signals:
        top = signals[0]
        summary_text += (
            f"，{top.risk_type}（偏离度 "
            f"{top.deviation_value:.1f}{top.deviation_unit}）"
        )
    parts.append(summary_text)
    parts.append("")

    # 3. 价格概览（2列）
    parts.append(f"## {EmojiMap.AMOUNT} 核心看板")
    parts.append("")
    parts.append(_render_core_panel(stock, signals))
    parts.append("")

    # 4. 价格概览（2列）
    parts.append(f"## {EmojiMap.PRICE} 价格概览")
    parts.append("")
    parts.append(
        render_table(
            ["指标", "数值"],
            [
                ["当前价", format_price(stock.current_price, stock.market)],
                ["开盘价", format_price(stock.open_price, stock.market)],
                ["最高价", format_price(stock.high, stock.market)],
                ["最低价", format_price(stock.low, stock.market)],
                ["昨收价", format_price(stock.prev_close, stock.market)],
                ["振幅", f"{amplitude:.1f}%"],
            ],
            col_align=["left", "right"],
        )
    )
    parts.append("")

    # 5. 量价指标（段落列表）
    parts.append(f"## {EmojiMap.AMOUNT} 量价指标")
    parts.append("")
    emoji_c = change_emoji(stock.change_percent)
    parts.append(f"- {EmojiMap.CHANGE} 涨跌幅：{format_change_plain(stock.change_percent)} {emoji_c}")
    parts.append(f"- {EmojiMap.PRICE} 当前价：{format_price(stock.current_price, stock.market)}")
    parts.append(f"- {EmojiMap.AMOUNT} 成交量：{format_volume(stock.volume, stock.market)}")
    parts.append(f"- {EmojiMap.AMOUNT} 成交额：{format_amount(stock.amount, stock.market)}")
    parts.append(f"- {EmojiMap.VOLUME_RATIO} 量比：{format_volume_ratio(stock.volume_ratio)}")
    parts.append(f"- {EmojiMap.TURNOVER} 换手率：{format_turnover(stock.turnover_rate)}")
    parts.append("")

    # 6. 异动分析
    if signals:
        parts.append(f"## {EmojiMap.ANALYSIS} 异动分析")
        parts.append("")
        for sig in signals:
            symbol = risk_level_symbol(sig.level)
            parts.append(f"### {symbol} {sig.risk_type}")
            parts.append(f"{render_badge(fmt_signal_level(sig.level))} {render_signal_bar(sig.level)}")
            parts.append("")
            parts.append(f"{sig.description}（偏离度 {sig.deviation_value:.1f}{sig.deviation_unit}）。")
            parts.append("")
            # 补充可能的分析
            if "量比" in sig.risk_type:
                parts.append("可能原因：")
                parts.append("- 近期有重大消息或财报预期")
                parts.append("- 主力资金异动")
                parts.append("- 板块内部轮动")
                parts.append("")

    # 7. 风险提示
    if signals:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append(_risk_warnings(signals))
    else:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append("当前未检测到显著风险信号。")
        parts.append("")

    # 8. 操作建议
    parts.append(f"## {EmojiMap.CONCLUSION} 操作建议")
    parts.append("")
    max_level = max((s.level for s in signals), default=0)
    mk = stock.market
    if max_level >= 2:
        parts.append(f"{EmojiMap.OP_HOLD} **持有/观望**")
        parts.append("")
        parts.append(f"- 当前价：{format_price(stock.current_price, mk)}")
        parts.append(f"- 止损参考：{format_price(_stop_loss(stock.current_price), mk)}（-5%）")
        parts.append(f"- 目标参考：{format_price(_target_price(stock.current_price), mk)}（+5.6%）")
    elif max_level >= 1:
        parts.append(f"{EmojiMap.OP_BUY} **可关注**")
        parts.append("")
        parts.append(f"- 当前价：{format_price(stock.current_price, mk)}")
        parts.append(f"- 轻度异动，建议确认量能持续性后再决策")
    else:
        parts.append(f"{EmojiMap.OP_BUY} **正常持有**")
        parts.append("")
        parts.append(f"- 当前价：{format_price(stock.current_price, mk)}")
        parts.append("- 量价配合正常，按既定策略执行")
    parts.append("")
    parts.append("> 以上参考数值基于技术指标计算，不构成投资建议。")
    parts.append("")

    # 9. 关注维度汇总表
    parts.append(f"### 关注维度")
    parts.append("")
    parts.append(_dimension_table(stock, signals))
    parts.append("")

    # 10. 相关资讯（可选，详细模式用段落格式）
    if data.news:
        parts.append(_render_news_details(data))
        parts.append("")

    # 11. 数据来源
    parts.append(f"{EmojiMap.DATA_SOURCE} 数据来源：{data.data_source} | {EmojiMap.CLOCK} {data.timestamp}")

    return "\n".join(parts)
