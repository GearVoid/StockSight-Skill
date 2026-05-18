"""格式化公共工具

数值格式化、Emoji 映射、表格渲染等通用函数。
对标 VISUAL_SPECS.md Sections 2-5。
"""

from collections import Counter
from html import escape
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.types import NewsItem, StockData


# =============================================================================
# 市场与货币符号映射（VISUAL_SPECS Section 2 补充 - 跨市场）
# =============================================================================

MARKET_CURRENCY: Dict[str, str] = {
    "sh": "RMB",
    "sz": "RMB",
    "hk": "HKD",
    "us": "USD",
}

MARKET_TAGS: Dict[str, str] = {
    "sh": "A",
    "sz": "A",
    "hk": "H",
    "us": "U",
}


# =============================================================================
# Emoji 映射表（VISUAL_SPECS Section 2）
# =============================================================================

class EmojiMap:
    """Emoji 符号映射，每个符号绑定唯一语义"""

    # 行情状态
    UP = "📈"
    DOWN = "📉"
    FLAT = "➡️"
    ANOMALY = "🔥"

    # 核心指标
    PRICE = "💰"
    TURNOVER = "🔄"  # 换手率
    VOLUME_RATIO = "⚡"  # 量比
    AMOUNT = "📊"  # 成交额/量
    CHANGE = "📐"  # 涨跌幅

    # 状态与提示
    RISK = "⚠️"
    TIP = "💡"
    DATA_SOURCE = "📡"
    TAG = "🏷️"
    CLOCK = "🕐"

    # 区块标题
    REPORT = "📰"
    LIST = "📋"
    ANALYSIS = "🔍"
    CONCLUSION = "🎯"
    NOTE = "❓"
    NEWS = "🗞️"

    # 风险等级（VISUAL_SPECS Section 5.2）
    RISK_LEVELS = {1: "🔸", 2: "🔶", 3: "🔴"}

    # 操作建议（VISUAL_SPECS Section 5.3）
    OP_BUY = "🟢"
    OP_HOLD = "🟡"
    OP_SELL = "🔴"


def change_emoji(change_percent: float) -> str:
    """根据涨跌幅返回行情 emoji"""
    if change_percent > 0.05:
        return EmojiMap.UP
    elif change_percent < -0.05:
        return EmojiMap.DOWN
    return EmojiMap.FLAT


def risk_level_symbol(level: int) -> str:
    """风险等级数字 → emoji 符号"""
    return EmojiMap.RISK_LEVELS.get(level, "🔸")


def op_symbol(signal: str) -> str:
    """操作建议 → emoji 符号
    
    Args:
        signal: "buy", "hold", "sell"
    """
    mapping = {"buy": EmojiMap.OP_BUY, "hold": EmojiMap.OP_HOLD, "sell": EmojiMap.OP_SELL}
    return mapping.get(signal, EmojiMap.OP_HOLD)


# =============================================================================
# 数值格式化（VISUAL_SPECS Section 4.4）
# =============================================================================

def format_price(value: float, market: str = "") -> str:
    """价格格式化，保留2位小数，可选带货币前缀

    Args:
        value: 价格数值
        market: 市场标记（sh/sz/hk/us），非空时带上货币前缀

    Example:
        format_price(27.93) -> "27.93"
        format_price(27.93, "sh") -> "RMB 27.93"
        format_price(456.4, "hk") -> "HKD 456.40"
    """
    precision = 4 if market == "us" else 2
    formatted = f"{value:.{precision}f}"
    if market and market in MARKET_CURRENCY:
        return f"{MARKET_CURRENCY[market]} {formatted}"
    return formatted


def market_tag(market: str) -> str:
    """市场标记，如 A/H/U"""
    return MARKET_TAGS.get(market, "")


def format_change(value: float) -> str:
    """涨跌幅格式化，带符号+百分比
    
    Example: +3.2%, -2.1%
    """
    if value > 0:
        return f"+{value:.1f}% {EmojiMap.UP}"
    elif value < 0:
        return f"{value:.1f}% {EmojiMap.DOWN}"
    return f"±{value:.1f}% {EmojiMap.FLAT}"


def format_change_plain(value: float) -> str:
    """涨跌幅纯数值（不带 emoji），用于表格内部"""
    if value > 0:
        return f"+{value:.1f}%"
    return f"{value:.1f}%"


def format_volume(volume: int, market: str = "") -> str:
    """成交量格式化，按市场选择单位

    Args:
        volume: 成交量（股）
        market: 市场标记（sh/sz/hk/us）

    Example:
        A股: format_volume(23125400, "sh") -> "231.3万手"
                     (23125400股 / 100 = 231254手 / 10000 = 23.1万手)
                    实际: 23125400/1000000 = 23.1万手
        HK:  format_volume(26449868, "hk") -> "2645.0万股"
                    26449868股 / 10000 = 2645.0万股
        US:  format_volume(54862836, "us") -> "5486.3万股"
    """
    if market in ("hk", "us"):
        return f"{volume / 10000:.1f}万股"
    # A股: 股 → 手(÷100) → 万手(÷10000) = 股 ÷ 1000000
    return f"{volume / 1000000:.1f}万手"


def format_amount(amount: float, market: str = "") -> str:
    """成交额格式化，带货币前缀

    Args:
        amount: 成交额（万元）
        market: 市场标记

    Example:
        format_amount(64652, "sh") -> "RMB 64,652万"
        format_amount(11205362, "hk") -> "HKD 11,205,362万"
    """
    formatted = f"{amount:,.0f}万"
    if market and market in MARKET_CURRENCY:
        return f"{MARKET_CURRENCY[market]} {formatted}"
    return formatted


def format_turnover(value: float) -> str:
    """换手率格式化"""
    if value <= 0 or value > 100:
        return "—"
    return f"{value:.1f}%"


def format_volume_ratio(value: float) -> str:
    """量比格式化"""
    if value <= 0:
        return "—"
    return f"{value:.2f}"


# =============================================================================
# 信号等级格式化
# =============================================================================

def fmt_signal_level(level: int) -> str:
    """风险等级 → 格式化字符串"""
    symbol = risk_level_symbol(level)
    names = {1: "关注", 2: "警告", 3: "危险"}
    name = names.get(level, "未知")
    return f"{symbol} {name}"


def signal_level_label(level: int) -> str:
    """风险等级的文字标签。"""
    names = {1: "关注", 2: "警告", 3: "危险"}
    return names.get(level, "未知")


def render_badge(text: str) -> str:
    """渲染 GitHub Markdown 兼容的短标签"""
    return f"<kbd>{escape(str(text))}</kbd>"


def render_signal_bar(level: int, width: int = 5) -> str:
    """渲染风险/异动强度条。

    风险等级只有 0-3，但视觉条保留 5 格：关注=2格，警告=3格，危险=5格。
    """
    filled_by_level = {0: 0, 1: 2, 2: 3, 3: width}
    filled = filled_by_level.get(level, min(max(level, 0), width))
    return "▰" * filled + "▱" * (width - filled)


def render_count_bar(count: int, max_count: int, width: int = 5) -> str:
    """按数量渲染分布条，适合风险等级/信号构成聚合。"""
    if count <= 0 or max_count <= 0:
        filled = 0
    else:
        filled = max(1, round(count / max_count * width))
    return "▰" * filled + "▱" * (width - filled)


def risk_level_counts(signals: Iterable[object]) -> Dict[int, int]:
    """统计关注/警告/危险三个风险等级的信号数量。"""
    counts = Counter(getattr(sig, "level", 0) for sig in signals)
    return {level: counts.get(level, 0) for level in (1, 2, 3)}


def risk_type_counts(signals: Iterable[object]) -> List[Tuple[str, int, int]]:
    """按风险类型统计信号数量和该类型最高风险等级。"""
    grouped: Dict[str, List[int]] = {}
    for sig in signals:
        risk_type = str(getattr(sig, "risk_type", "未知信号") or "未知信号")
        grouped.setdefault(risk_type, []).append(int(getattr(sig, "level", 0) or 0))
    return sorted(
        ((risk_type, len(levels), max(levels)) for risk_type, levels in grouped.items()),
        key=lambda item: (-item[1], -item[2], item[0]),
    )


def render_risk_distribution(signals: Sequence[object]) -> str:
    """渲染 Markdown 风险等级分布条。"""
    if not signals:
        return f"{EmojiMap.OP_BUY} 暂无显著异动信号，风险分布保持平稳。"

    counts = risk_level_counts(signals)
    max_count = max(counts.values(), default=0)
    headers = [render_badge(label) for label in ("关注", "警告", "危险")]
    rows = [[
        f"{counts[1]} {render_count_bar(counts[1], max_count)}",
        f"{counts[2]} {render_count_bar(counts[2], max_count)}",
        f"{counts[3]} {render_count_bar(counts[3], max_count)}",
    ]]
    return render_table(headers, rows, col_align=["center", "center", "center"])


def render_signal_composition(signals: Sequence[object]) -> str:
    """渲染 Markdown 信号构成表。"""
    composition = risk_type_counts(signals)
    if not composition:
        return f"{EmojiMap.OP_BUY} 暂无显著异动信号。"

    max_count = max((count for _, count, _ in composition), default=0)
    rows = [
        [
            render_badge(risk_type),
            str(count),
            fmt_signal_level(level),
            render_count_bar(count, max_count),
        ]
        for risk_type, count, level in composition
    ]
    return render_table(
        ["信号类型", "数量", "最高等级", "分布"],
        rows,
        col_align=["left", "right", "left", "left"],
    )


def metric_quality_notes(stocks: Sequence[object]) -> List[str]:
    """识别不可用或明显异常的指标，供 Markdown/HTML 报告共同展示。"""
    notes: List[str] = []
    volume_ratio_codes = [
        str(getattr(stock, "code", ""))
        for stock in stocks
        if getattr(stock, "volume_ratio", 0) <= 0
    ]
    turnover_codes = [
        str(getattr(stock, "code", ""))
        for stock in stocks
        if getattr(stock, "turnover_rate", 0) <= 0 or getattr(stock, "turnover_rate", 0) > 100
    ]

    if volume_ratio_codes:
        notes.append(f"量比不可用：{', '.join(volume_ratio_codes)} 已显示为 —。")
    if turnover_codes:
        notes.append(f"换手率不可用或超出常规范围：{', '.join(turnover_codes)} 已显示为 —，不纳入风险判断。")
    return notes


def render_metric_strip(metrics: Sequence[Tuple[str, str]]) -> str:
    """渲染顶部指标摘要条，最多 5 个指标。"""
    if not metrics:
        return ""
    if len(metrics) > 5:
        raise ValueError("指标摘要条最多支持5个指标")
    headers = [render_badge(label) for label, _ in metrics]
    values = [value for _, value in metrics]
    return render_table(headers, [values], col_align=["center"] * len(metrics))


# =============================================================================
# 表格渲染（VISUAL_SPECS Section 4）
# =============================================================================

def render_table(
    headers: List[str],
    rows: List[List[str]],
    col_align: Optional[List[str]] = None,
) -> str:
    """渲染 Markdown 表格
    
    Args:
        headers: 表头列表，如 ['股票', '现价', '涨跌幅']
        rows: 数据行，每行是字符串列表
        col_align: 列对齐方式，'left' / 'right' / 'center'
                  默认全部左对齐
        
    Returns:
        格式化的 Markdown 表格字符串
        
    Raises:
        ValueError: 列数不一致或超过5列
    """
    n_cols = len(headers)

    if n_cols > 5:
        raise ValueError(f"表格列数不能超过5（当前{n_cols}列）")

    # 检查行数据列数
    for i, row in enumerate(rows):
        if len(row) != n_cols:
            raise ValueError(
                f"第{i+1}行列数({len(row)})与表头({n_cols})不一致"
            )

    if col_align is None:
        col_align = ["left"] * n_cols

    # 构建分隔符行
    align_map = {"left": ":---", "right": "---:", "center": ":---:"}
    separators = [align_map.get(a, ":---") for a in col_align]

    # 渲染
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(separators) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


# =============================================================================
# Markdown 报告公共渲染函数
# =============================================================================

def render_highest_risk_badge(signals: Sequence[object]) -> str:
    """整份报告最高风险标签。"""
    max_level = max((getattr(sig, "level", 0) for sig in signals), default=0)
    if max_level == 0:
        return f"{EmojiMap.OP_BUY} {render_badge('平稳')}"
    return f"{fmt_signal_level(max_level)} {render_signal_bar(max_level)}"


def render_data_quality_section(stocks: Sequence[StockData]) -> str:
    """渲染数据完整性提示区块。"""
    notes = metric_quality_notes(stocks)
    if not notes:
        return ""
    lines = [f"## {EmojiMap.TIP} 数据完整性", ""]
    lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines)


def render_news_details_standard(news: Sequence[NewsItem]) -> str:
    """渲染标准模式可折叠新闻区块。"""
    if not news:
        return ""
    news_headers = ["来源", "标题", "时间"]
    news_rows = [[n.source or "—", n.title or "—", n.published_at or "—"] for n in news[:5]]
    return "\n".join([
        "<details>",
        f"<summary>{EmojiMap.NEWS} 相关资讯</summary>",
        "",
        render_table(news_headers, news_rows),
        "",
        "</details>",
    ])


def render_news_details_detailed(news: Sequence[NewsItem]) -> str:
    """渲染详细模式可折叠新闻区块。"""
    if not news:
        return ""
    lines = [
        "<details>",
        f"<summary>{EmojiMap.NEWS} 相关资讯</summary>",
        "",
    ]
    for item in news[:5]:
        title = item.title or "—"
        source = item.source or "—"
        time = f"（{item.published_at}）" if item.published_at else ""
        lines.append(f"[{source}] {title}{time}")
        if item.snippet:
            lines.append(f"  {EmojiMap.NOTE} {item.snippet}")
        lines.append("")
    lines.append("</details>")
    return "\n".join(lines)
