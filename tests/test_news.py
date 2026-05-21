# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from news.aggregator import (
    NewsAggregator,
    _dedupe_key,
    _tag_snippet,
    create_configured_news_provider,
)
from news.hard_info import classify_category, classify_source, is_hard_info
from news.base import NewsProvider
from core import NewsItem
from tests.fixtures import sample_stock


class FakeNewsProvider(NewsProvider):
    """A fake news provider for testing the aggregator."""
    def __init__(self, results=None):
        self._results = results or []
        self.last_query = None

    def name(self) -> str:
        return "Fake"

    def search(self, query: str, max_results: int = 5):
        self.last_query = query
        return self._results[:max_results]


class DedupeKeyTests(unittest.TestCase):
    def test_same_url_produces_same_key(self):
        a = NewsItem(title="A", source="X", url="https://example.com/a")
        b = NewsItem(title="B", source="Y", url="https://example.com/a")
        self.assertEqual(_dedupe_key(a), _dedupe_key(b))

    def test_different_url_produces_different_key(self):
        a = NewsItem(title="A", source="X", url="https://example.com/a")
        b = NewsItem(title="A", source="X", url="https://example.com/b")
        self.assertNotEqual(_dedupe_key(a), _dedupe_key(b))

    def test_no_url_falls_back_to_source_title(self):
        item = NewsItem(title="T", source="S", url="")
        self.assertEqual(_dedupe_key(item), "s|t")


class TagSnippetTests(unittest.TestCase):
    def test_adds_kind_tag_to_empty_snippet(self):
        item = NewsItem(title="T", source="S", url="", snippet="")
        result = _tag_snippet("公告", item)
        self.assertIn("[公告]", result.snippet)
        self.assertIn("来源可信度", result.snippet)

    def test_prepends_kind_tag_to_existing_snippet(self):
        item = NewsItem(title="T", source="S", url="", snippet="some content")
        result = _tag_snippet("异动", item)
        self.assertEqual(result.snippet, "[新闻] some content")

    def test_does_not_double_tag(self):
        item = NewsItem(title="T", source="S", url="", snippet="[公告] already tagged")
        result = _tag_snippet("公告", item)
        self.assertEqual(result.snippet, "[公告] already tagged")


class NewsAggregatorTests(unittest.TestCase):
    def test_aggregator_with_none_provider_returns_empty(self):
        agg = NewsAggregator(provider=None)
        stock = sample_stock()
        result = agg.search_for_stocks([stock])
        self.assertEqual(result, [])

    def test_aggregator_with_empty_stocks_returns_empty(self):
        provider = FakeNewsProvider([NewsItem(title="T", source="S", url="u")])
        agg = NewsAggregator(provider=provider)
        result = agg.search_for_stocks([])
        self.assertEqual(result, [])

    def test_aggregator_with_zero_max_results_returns_empty(self):
        provider = FakeNewsProvider([NewsItem(title="T", source="S", url="u")])
        agg = NewsAggregator(provider=provider)
        stock = sample_stock()
        result = agg.search_for_stocks([stock], max_results=0)
        self.assertEqual(result, [])

    def test_aggregator_dedupes_by_url(self):
        item = NewsItem(title="Same", source="S", url="https://dup.com")
        provider = FakeNewsProvider([item, item, item])
        agg = NewsAggregator(provider=provider)
        stock = sample_stock()

        result = agg.search_for_stocks([stock], max_results=5)

        self.assertEqual(len(result), 1)

    def test_aggregator_respects_max_results(self):
        items = [
            NewsItem(title=f"T{i}", source="S", url=f"https://x.com/{i}")
            for i in range(10)
        ]
        provider = FakeNewsProvider(items)
        agg = NewsAggregator(provider=provider)
        stock = sample_stock()

        result = agg.search_for_stocks([stock], max_results=3)

        self.assertLessEqual(len(result), 3)

    def test_aggregator_searches_all_query_types(self):
        provider = FakeNewsProvider([
            NewsItem(title="T", source="S", url="https://a.com"),
        ])
        agg = NewsAggregator(provider=provider)
        stock = sample_stock(name="平安银行", code="000001")

        result = agg.search_for_stocks([stock], max_results=10, query_types=["公告"])

        self.assertGreaterEqual(len(result), 1)
        self.assertIn("000001", provider.last_query)

    def test_aggregator_ranks_hard_info_before_generic_news(self):
        provider = FakeNewsProvider([
            NewsItem(title="普通新闻", source="某网站", url="https://x.com/news"),
            NewsItem(title="平安银行年度报告公告", source="东方财富", url="https://data.eastmoney.com/notices/detail/000001/a.html"),
        ])
        agg = NewsAggregator(provider=provider)
        stock = sample_stock(name="平安银行", code="000001")

        result = agg.search_for_stocks([stock], max_results=2, query_types=["公告"])

        self.assertEqual(result[0].title, "平安银行年度报告公告")
        self.assertTrue(is_hard_info(result[0]))

    def test_create_configured_news_provider_returns_none_when_not_configured(self):
        with patch("news.aggregator.get_active_provider", return_value=None):
            provider = create_configured_news_provider()
        self.assertIsNone(provider)


if __name__ == "__main__":
    unittest.main()

# ---------------------------------------------------------------------------
# Tavily / SerpAPI provider response parsing tests
# ---------------------------------------------------------------------------

from news.providers.tavily import TavilyNewsProvider
from news.providers.serpapi import SerpapiNewsProvider


TAVILY_RESPONSE = {
    "results": [
        {
            "title": "恒生电子发布财报",
            "source": "东方财富",
            "url": "https://example.com/1",
            "published_date": "2026-05-19",
            "content": "恒生电子公布2026年Q1财报...",
        },
        {
            "title": "恒生电子异动公告",
            "source": "新浪财经",
            "url": "https://example.com/2",
            "published_date": "2026-05-18",
            "content": "恒生电子股价异动...",
        },
    ]
}

SERPAPI_RESPONSE = {
    "news_results": [
        {
            "title": "Tencent Q1 Earnings Beat",
            "source": "Reuters",
            "link": "https://example.com/t1",
            "date": "2026-05-19",
            "snippet": "Tencent reported...",
        },
    ]
}


class TavilyProviderTests(unittest.TestCase):
    def test_search_parses_results(self):
        class FakeSession:
            def post(self, url, json, headers, timeout):
                class FakeResp:
                    status_code = 200
                    @staticmethod
                    def json():
                        return TAVILY_RESPONSE
                return FakeResp()

        provider = TavilyNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("恒生电子", max_results=5)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "恒生电子发布财报")
        self.assertEqual(items[0].source, "东方财富")
        self.assertEqual(items[0].url, "https://example.com/1")

    def test_search_returns_empty_on_http_error(self):
        class FakeSession:
            def post(self, url, json, headers, timeout):
                class FakeResp:
                    status_code = 500
                    text = "error"
                return FakeResp()

        provider = TavilyNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("test", max_results=5)
        self.assertEqual(items, [])

    def test_search_returns_empty_on_request_error(self):
        class FakeSession:
            def post(self, url, json, headers, timeout):
                raise Exception("timeout")

        provider = TavilyNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("test", max_results=5)
        self.assertEqual(items, [])

    def test_name_is_tavily(self):
        provider = TavilyNewsProvider(api_key="test-key")
        self.assertEqual(provider.name(), "Tavily")


class SerpapiProviderTests(unittest.TestCase):
    def test_search_parses_results(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                class FakeResp:
                    status_code = 200
                    @staticmethod
                    def json():
                        return SERPAPI_RESPONSE
                return FakeResp()

        provider = SerpapiNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("Tencent", max_results=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Tencent Q1 Earnings Beat")
        self.assertEqual(items[0].url, "https://example.com/t1")

    def test_search_returns_empty_on_http_error(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                class FakeResp:
                    status_code = 403
                    text = "forbidden"
                return FakeResp()

        provider = SerpapiNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("test", max_results=5)
        self.assertEqual(items, [])

    def test_search_returns_empty_on_request_error(self):
        class FakeSession:
            def get(self, url, params, headers, timeout):
                raise Exception("timeout")

        provider = SerpapiNewsProvider(api_key="test-key")
        provider._session = FakeSession()

        items = provider.search("test", max_results=5)
        self.assertEqual(items, [])

    def test_name_is_serpapi(self):
        provider = SerpapiNewsProvider(api_key="test-key")
        self.assertEqual(provider.name(), "SerpAPI")


class HardInfoClassificationTests(unittest.TestCase):
    def test_classifies_cninfo_as_high_confidence_source(self):
        item = NewsItem(
            title="年度报告",
            source="巨潮资讯",
            url="https://www.cninfo.com.cn/new/disclosure/detail",
        )

        self.assertEqual(classify_source(item), "巨潮资讯")
        self.assertEqual(classify_category(item), "财报")

    def test_classifies_risk_tip_from_title(self):
        item = NewsItem(title="关于股票交易风险提示公告", source="上交所")

        self.assertEqual(classify_category(item), "风险提示")
        self.assertTrue(is_hard_info(item))
