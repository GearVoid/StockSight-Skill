"""标准模式报告渲染

对标 VISUAL_SPECS.md Section 6.2（标准模式）和 Section 8（完整示例）。

报告结构（固定顺序）:
  1. H1: 📰 标题
  2. 引用摘要
  3. H2: 📋 异动股票列表（表格，5列）
  4. H2: ⚠️ 风险提示（表格，4列）
  5. H2: 🎯 操作建议（段落）
  6. 数据来源标注
"""

from typing import List

from core import RiskSignal, StockData, ReportData
from .base import (
    EmojiMap,
    change_emoji,
    format_change_plain,
    format_price,
    format_volume_ratio,
    format_turnover,
    market_tag,
    risk_level_symbol,
    render_table,
)


def _anomaly_flag(stock: StockData, signals: List[RiskSignal]) -> str:
    """判断股票是否在异动信号中，返回原因标识"""
    risk_types = []
    for signal in signals:
        if signal.stock_code == stock.code:
            risk_types.append(signal.risk_type)
    if risk_types:
        return f"{' + '.join(risk_types)} {EmojiMap.ANOMALY}"
    return "—"


def _build_stock_table(stocks: List[StockData], signals: List[RiskSignal]) -> str:
    """渲染异动股票列表（5列）"""
    headers = ["股票", "现价", "涨跌幅", "量比", "异动信号"]
    rows = []
    for s in stocks:
        change_str = format_change_plain(s.change_percent)
        emoji = change_emoji(s.change_percent)
        rows.append([
            f"{s.code} {s.name}",
            format_price(s.current_price),
            f"{change_str} {emoji}",
            format_volume_ratio(s.volume_ratio),
            _anomaly_flag(s, signals),
        ])
    return render_table(headers, rows, col_align=["left", "right", "right", "right", "left"])


def _build_risk_table(signals: List[RiskSignal]) -> str:
    """渲染风险提示表格（4列）"""
    if not signals:
        return ""
    headers = ["股票", "风险类型", "偏离说明", "等级"]
    rows = []
    for sig in signals:
        level_symbol = risk_level_symbol(sig.level)
        unit = sig.deviation_unit
        dev_str = f"{sig.deviation_value:.1f}{unit}" if unit else f"{sig.deviation_value:.1f}"
        rows.append([
            sig.stock_code,
            sig.risk_type,
            f"{sig.description}（偏离度 {dev_str}）",
            level_symbol,
        ])
    return render_table(headers, rows)


def _build_suggestions(stocks: List[StockData], signals: List[RiskSignal]) -> str:
    """生成操作建议段落"""
    lines = []
    for stock in stocks:
        change = stock.change_percent
        level = 0
        for sig in signals:
            if sig.stock_code == stock.code:
                level = max(level, sig.level)

        code_name = f"{stock.code} {stock.name}"
        if level >= 3:
            symbol = EmojiMap.OP_SELL
            advice = "风险过高，建议关注后续走势后决策"
        elif level >= 2:
            symbol = EmojiMap.OP_HOLD
            advice = "异动特征明显，建议确认方向后再操作"
        elif change > 3:
            symbol = EmojiMap.OP_HOLD
            advice = "涨幅较大，注意回调风险"
        else:
            symbol = EmojiMap.OP_BUY
            advice = "量价正常，按既定策略执行"

        lines.append(f"{symbol} {code_name}：{advice}")

    return "\n".join(lines)


def render_standard_report(data: ReportData) -> str:
    """渲染标准模式报告
    
    Args:
        data: 报告数据包
        
    Returns:
        ️ 格式化后的 Markdown 报告文本
    """
    parts = []

    # 1. H1: 标题
    parts.append(f"# {EmojiMap.REPORT} {data.title}")
    parts.append("")

    # 2. 引用摘要
    parts.append(f"> {EmojiMap.REPORT} 一句话总结：{data.summary}")
    parts.append("")

    # 3. 异动股票列表
    parts.append(f"## {EmojiMap.LIST} 异动股票列表")
    parts.append("")

    # 先找有信号的股票，再补无信号的
    signal_codes = {s.stock_code for s in data.signals}
    anomaly_stocks = [s for s in data.stocks if s.code in signal_codes]
    normal_stocks = [s for s in data.stocks if s.code not in signal_codes]
    ordered_stocks = anomaly_stocks + normal_stocks

    # 渲染表格（传递 signals 给 _anomaly_flag）
    headers = ["股票", "现价", "涨跌幅", "量比", "异动信号"]
    rows = []
    for s in ordered_stocks:
        change_str = format_change_plain(s.change_percent)
        emoji = change_emoji(s.change_percent)
        tag_value = market_tag(s.market)
        tag = f" [{tag_value}]" if tag_value else ""
        rows.append([
            f"{s.code} {s.name}{tag}",
            format_price(s.current_price, s.market),
            f"{change_str} {emoji}",
            format_volume_ratio(s.volume_ratio),
            _anomaly_flag(s, data.signals),
        ])
    parts.append(render_table(headers, rows, col_align=["left", "right", "right", "right", "left"]))
    parts.append("")

    # 4. 风险提示
    if data.signals:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        risk_table = _build_risk_table(data.signals)
        if risk_table:
            parts.append(risk_table)
            parts.append("")
    else:
        parts.append(f"## {EmojiMap.RISK} 风险提示")
        parts.append("")
        parts.append("✅ 未发现显著异动，当前市场状态平稳。")
        parts.append("")

    # 5. 操作建议
    if data.signals:
        parts.append(f"## {EmojiMap.CONCLUSION} 操作建议")
        parts.append("")
        parts.append(_build_suggestions(data.stocks, data.signals))
        parts.append("")

    # 6. 相关资讯（可选）
    if data.news:
        parts.append(f"## {EmojiMap.NEWS} 相关资讯")
        parts.append("")
        news_headers = ["来源", "标题", "时间"]
        news_rows = []
        for n in data.news[:5]:
            news_rows.append([n.source, n.title, n.published_at])
        parts.append(render_table(news_headers, news_rows))
        parts.append("")

    # 7. 数据来源标注
    parts.append(f"{EmojiMap.DATA_SOURCE} 数据来源：{data.data_source} | {EmojiMap.CLOCK} {data.timestamp}")

    return "\n".join(parts)
