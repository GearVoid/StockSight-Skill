"""核心数据类型定义"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NewsItem:
    """一条新闻条目

    Args:
        title: 新闻标题
        source: 来源名称（如"新浪财经"）
        url: 原文链接（可选）
        published_at: 发布时间（如"2小时前"或"05-17 21:30"）
        snippet: 摘要文本（可选，详细模式使用）
    """
    title: str
    source: str
    url: str = ""
    published_at: str = ""
    snippet: str = ""


@dataclass
class StockData:
    """标准化的股票数据，所有数据源统一输出此格式"""

    code: str
    """股票代码，如 '600570'"""

    name: str
    """股票名称"""

    current_price: float
    """当前价格（元）"""

    prev_close: float
    """昨日收盘价（元）"""

    open_price: float
    """今日开盘价（元）"""

    high: float
    """今日最高价（元）"""

    low: float
    """今日最低价（元）"""

    volume: int
    """成交量（手）"""

    amount: float
    """成交额（万元）"""

    volume_ratio: float
    """量比"""

    change_percent: float
    """涨跌幅（%）"""

    turnover_rate: float
    """换手率（%）"""

    timestamp: str
    """数据时间，格式 'YYYY-MM-DD HH:MM:SS'"""

    market: str = ""
    """市场标记: 'sh' 沪市, 'sz' 深市, 'hk' 港股, 'us' 美股（可选，默认空字符串）"""

    raw: Optional[dict] = field(default=None)
    """原始数据（调试用，可选）"""


@dataclass
class RiskSignal:
    """异动信号 — detector 输出给 formatter 的核心数据结构"""

    stock_code: str
    """触发异动的股票代码"""

    risk_type: str
    """风险类型，如 '量比偏离' / '换手率偏高' / '超额收益异动'"""

    level: int
    """风险等级: 1=关注🔸, 2=警告🔶, 3=危险🔴"""

    deviation_value: float
    """偏离度数值"""

    deviation_unit: str
    """偏离度单位: '%' 或 'σ'"""

    description: str
    """可读的描述文本，如 '量比2.15，超过板块均值1.2倍'"""


@dataclass
class ReportData:
    """报告数据 — 传给 formatter 渲染的完整数据包"""

    title: str
    """报告标题"""

    summary: str
    """一句话摘要（模板填空生成）"""

    stocks: List[StockData]
    """参与分析的股票列表"""

    signals: List[RiskSignal]
    """detector 检测到的异动信号"""

    data_source: str
    """数据来源名称"""

    timestamp: str
    """报告生成时间"""

    news: List[NewsItem] = field(default_factory=list)
    """相关新闻列表（可选，由 NewsProvider 搜索填充）"""
