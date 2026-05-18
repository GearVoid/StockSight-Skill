"""格式化公共工具

数值格式化、Emoji 映射、表格渲染等通用函数。
对标 VISUAL_SPECS.md Sections 2-5。
"""

from typing import Dict, List, Optional


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
