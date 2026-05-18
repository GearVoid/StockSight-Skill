"""News 新闻搜索模块"""

from .base import NewsProvider
from .aggregator import NewsAggregator, create_configured_news_provider, search_configured_news

__all__ = [
    "NewsProvider",
    "NewsAggregator",
    "create_configured_news_provider",
    "search_configured_news",
]
