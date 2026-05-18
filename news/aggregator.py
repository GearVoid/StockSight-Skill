"""News and announcement aggregation helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set

from core import NewsItem, StockData
from core.config import get_active_provider, get_api_key
from .base import NewsProvider


NEWS_QUERY_TYPES = {
    "公告": "{name} {code} 公告 交易所",
    "财报": "{name} {code} 财报 业绩 净利润",
    "异动": "{name} {code} 股票 异动 涨停 跌停",
}


def create_configured_news_provider() -> Optional[NewsProvider]:
    """Create the configured optional news provider, or None."""
    provider_name = get_active_provider()
    if not provider_name:
        return None

    api_key = get_api_key(provider_name)
    if not api_key:
        return None

    if provider_name == "tavily":
        from .providers import TavilyNewsProvider

        return TavilyNewsProvider(api_key)
    if provider_name == "serpapi":
        from .providers import SerpapiNewsProvider

        return SerpapiNewsProvider(api_key)
    return None


def _dedupe_key(item: NewsItem) -> str:
    if item.url:
        return item.url.strip().lower()
    return f"{item.source}|{item.title}".strip().lower()


def _tag_snippet(kind: str, item: NewsItem) -> NewsItem:
    if not item.snippet:
        item.snippet = f"{kind}相关资讯。"
    elif not item.snippet.startswith(f"[{kind}]"):
        item.snippet = f"[{kind}] {item.snippet}"
    return item


class NewsAggregator:
    """Search announcement, earnings, and anomaly news with dedupe."""

    def __init__(self, provider: Optional[NewsProvider] = None):
        self.provider = provider

    def search_for_stocks(
        self,
        stocks: Sequence[StockData],
        max_results: int = 5,
        query_types: Optional[Iterable[str]] = None,
    ) -> List[NewsItem]:
        if self.provider is None or not stocks or max_results <= 0:
            return []

        kinds = list(query_types or NEWS_QUERY_TYPES.keys())
        seen: Set[str] = set()
        items: List[NewsItem] = []

        per_query_limit = max(1, min(3, max_results))
        for stock in stocks:
            for kind in kinds:
                template = NEWS_QUERY_TYPES.get(kind)
                if not template:
                    continue
                query = template.format(name=stock.name, code=stock.code)
                for item in self.provider.search(query, max_results=per_query_limit):
                    key = _dedupe_key(item)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    items.append(_tag_snippet(kind, item))
                    if len(items) >= max_results:
                        return items

        return items


def search_configured_news(
    stocks: Sequence[StockData],
    max_results: int = 5,
    query_types: Optional[Iterable[str]] = None,
) -> List[NewsItem]:
    """Search news using configured provider and safe degradation."""
    provider = create_configured_news_provider()
    return NewsAggregator(provider).search_for_stocks(stocks, max_results, query_types)
