"""东方财富数据源

支持 A 股实时行情 + 行业/概念板块基准数据。
数据来源: push2.eastmoney.com (JSON API)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

from core import DataSource, DataSourceError, FetchResult, StockData
from core.market import to_eastmoney_secid

logger = logging.getLogger(__name__)

# =============================================================================
# API 端点与常量
# =============================================================================

STOCK_QUERY_URL = "https://push2.eastmoney.com/api/qt/stock/get"
SECTOR_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
SECTOR_CONSTIT_URL = "https://push2.eastmoney.com/api/qt/clist/get"

UT = "fa5fd1943c7b386f172d6893dbfba10b"
HEADERS = {
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# stock/get 字段编码
FIELDS_STOCK = (
    "f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f127,f128,f129,f167,f168"
)

# clist/get 字段：板块列表
FIELDS_SECTOR = "f12,f14,f2,f3,f4"

# clist/get 字段：板块成分
FIELDS_CONSTITUENT = "f12,f14,f50,f167,f168"


def _to_secid(code: str) -> Optional[str]:
    return to_eastmoney_secid(code)


class EastMoneyDataSource(DataSource):
    """东方财富数据源（A 股 + 板块基准）

    提供 A 股实时行情和行业板块基准数据。
    作为 Tencent 数据源的备用/补充，提供板块基准能力。
    """

    def __init__(self, timeout: int = 10, max_retries: int = 2):
        self._session = requests.Session()
        self._timeout = timeout
        self._max_retries = max_retries
        # 板块缓存: {BK代码: 板块名}
        self._sector_cache: Optional[List[Dict]] = None
        # 板块成分缓存: {BK代码: StockData均值}
        self._constituent_cache: Dict[str, StockData] = {}

    def name(self) -> str:
        return "东方财富"

    # ------------------------------------------------------------------
    # 核心数据获取
    # ------------------------------------------------------------------

    def fetch(
        self,
        codes: List[str],
        **kwargs,
    ) -> FetchResult:
        """获取 A 股实时行情

        Args:
            codes: 股票代码列表（仅 6 位 A 股代码）

        Returns:
            (data_map, failed_list)
        """
        if not codes:
            return {}, []

        result: Dict[str, StockData] = {}
        failed: List[str] = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for code in codes:
            secid = _to_secid(code)
            if secid is None:
                failed.append(code)
                continue

            try:
                stock = self._fetch_single(code, secid, ts)
                if stock is not None:
                    result[code] = stock
                else:
                    failed.append(code)
            except DataSourceError:
                failed.append(code)

        return result, failed

    def _fetch_single(
        self, code: str, secid: str, timestamp: str
    ) -> Optional[StockData]:
        """获取单个股票实时行情"""
        params = {
            "secid": secid,
            "ut": UT,
            "fields": FIELDS_STOCK,
        }

        raw_data = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(
                    STOCK_QUERY_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=self._timeout,
                )
                resp.encoding = "utf-8"
                d = resp.json()
                if d.get("rc") == 0 and d.get("data"):
                    raw_data = d["data"]
                    break
                else:
                    logger.warning(
                        "东财API返回异常 [%s] rc=%s", code, d.get("rc")
                    )
            except Exception as e:
                logger.warning(
                    "东财请求失败 [%s](第%d次): %s", code, attempt + 1, e
                )

        if raw_data is None:
            return None

        # 字段解码（所有价格字段 × 0.01）
        price_scale = 0.01
        market = "sh" if code.startswith("6") else "sz"

        # 基础行情字段
        current_price = (raw_data.get("f43") or 0) * price_scale
        high = (raw_data.get("f44") or 0) * price_scale
        low = (raw_data.get("f45") or 0) * price_scale
        open_price = (raw_data.get("f46") or 0) * price_scale
        volume = int(raw_data.get("f47") or 0)  # 手
        amount = (raw_data.get("f48") or 0) / 10000  # 元→万元
        volume_ratio = (raw_data.get("f50") or 0) * 0.01
        prev_close = (raw_data.get("f60") or 0) * price_scale
        change_percent = (raw_data.get("f168") or 0) * 0.01
        turnover_rate = (raw_data.get("f167") or 0) * 0.01

        # 行业板块信息
        industry = raw_data.get("f127", "")
        concepts = [
            s.strip()
            for s in (raw_data.get("f129", "") or "").split(",")
            if s.strip()
        ]

        return StockData(
            code=code,
            name=raw_data.get("f58", ""),
            current_price=current_price,
            prev_close=prev_close,
            open_price=open_price,
            high=high,
            low=low,
            volume=volume * 100,  # 手→股
            amount=amount,
            volume_ratio=volume_ratio,
            change_percent=change_percent,
            turnover_rate=turnover_rate,
            timestamp=timestamp,
            market=market,
            raw={
                "industry": industry,
                "concepts": concepts,
                "f127": industry,
                "f129": concepts,
            },
        )

    # ------------------------------------------------------------------
    # 板块数据
    # ------------------------------------------------------------------

    def get_sector_list(self) -> List[Dict]:
        """获取行业板块列表（单页，最多前100个）

        注意：clist/get API 有反爬限制，可能返回空。
        板块数据为增强功能，不影响核心行情获取。

        Returns:
            [{code: "BK1408", name: "软件开发", change: 1.25}]
        """
        if self._sector_cache is not None:
            return self._sector_cache

        sectors = []

        try:
            params = {
                "pn": "1",
                "pz": "100",
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90+t:2",  # 行业板块
                "fields": FIELDS_SECTOR,
            }
            resp = self._session.get(
                SECTOR_LIST_URL,
                params=params,
                headers={
                    "Referer": "https://data.eastmoney.com/",
                    "User-Agent": HEADERS["User-Agent"],
                },
                timeout=self._timeout,
            )
            d = resp.json()
            if d.get("rc") != 0:
                logger.warning(
                    "东财板块列表获取失败 rc=%s", d.get("rc")
                )
                return []

            items = d.get("data", {}).get("diff", [])
            for item in items:
                sectors.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "index_price": item.get("f2"),
                    "change": item.get("f3"),
                })

            self._sector_cache = sectors
            return sectors
        except Exception as e:
            logger.warning("东财板块列表异常: %s", e)
            return []

    def get_sector_benchmark(self, code: str) -> Optional[StockData]:
        """获取个股所在行业的板块基准

        通过股票代码获取行业板块（f127），再获取该板块的成分股均值，
        构造一个虚拟的"板块代理" StockData。

        Args:
            code: A 股代码，如 '600570'

        Returns:
            板块代理 StockData（仅 change_percent/volume_ratio/turnover_rate 有效），
            查询失败返回 None
        """
        # Step 1: 获取股票信息，提取行业名 f127
        secid = _to_secid(code)
        if secid is None:
            return None

        params = {
            "secid": secid,
            "ut": UT,
            "fields": "f127,f129",
        }
        try:
            resp = self._session.get(
                STOCK_QUERY_URL,
                params=params,
                headers=HEADERS,
                timeout=self._timeout,
            )
            d = resp.json()
            if d.get("rc") != 0:
                return None
            industry_name = d.get("data", {}).get("f127", "")
            if not industry_name:
                return None
        except Exception as e:
            logger.debug("获取行业名失败 [%s]: %s", code, e)
            return None

        # Step 2: 从板块列表中找到匹配的板块代码
        sectors = self.get_sector_list()
        bk_code = None
        for sec in sectors:
            if sec.get("name") == industry_name:
                bk_code = sec.get("code")
                break

        if bk_code is None:
            logger.debug("未找到板块匹配 [%s → %s]", code, industry_name)
            return None

        # Step 3: 获取板块成分股并计算均值（单页，最多200只）
        if bk_code in self._constituent_cache:
            return self._constituent_cache[bk_code]

        constituents = []
        try:
            params_const = {
                "pn": "1",
                "pz": "200",
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": f"b:{bk_code}",
                "fields": FIELDS_CONSTITUENT,
            }
            resp = self._session.get(
                SECTOR_CONSTIT_URL,
                params=params_const,
                headers={
                    "Referer": "https://data.eastmoney.com/",
                    "User-Agent": HEADERS["User-Agent"],
                },
                timeout=self._timeout,
            )
            d = resp.json()
            if d.get("rc") != 0:
                return None

            constituents = d.get("data", {}).get("diff", [])
            if not constituents:
                return None

            # 计算均值
            vrs = [
                (c.get("f50") or 0) * 0.01
                for c in constituents
                if (c.get("f50") or 0) > 0
            ]
            trs = [
                (c.get("f167") or 0) * 0.01
                for c in constituents
                if (c.get("f167") or 0) > 0
            ]
            changes = [
                (c.get("f168") or 0) * 0.01
                for c in constituents
                if c.get("f168") is not None
            ]

            avg_vr = sum(vrs) / len(vrs) if vrs else 0.0
            avg_tr = sum(trs) / len(trs) if trs else 0.0
            avg_change = sum(changes) / len(changes) if changes else 0.0

            benchmark = StockData(
                code=bk_code,
                name=industry_name,
                current_price=0.0,
                prev_close=0.0,
                open_price=0.0,
                high=0.0,
                low=0.0,
                volume=0,
                amount=0.0,
                volume_ratio=avg_vr,
                change_percent=avg_change,
                turnover_rate=avg_tr,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                market="",  # 板块，非个股
                raw={"type": "sector_benchmark", "bk_code": bk_code},
            )
            self._constituent_cache[bk_code] = benchmark
            return benchmark

        except Exception as e:
            logger.debug("板块成分获取失败 [%s]: %s", bk_code, e)
            return None

    def get_sector_benchmarks(
        self, codes: List[str]
    ) -> Dict[str, Optional[StockData]]:
        """批量获取板块基准

        Args:
            codes: 股票代码列表

        Returns:
            {code: StockData 或 None}
        """
        result = {}
        for code in codes:
            result[code] = self.get_sector_benchmark(code)
        return result
