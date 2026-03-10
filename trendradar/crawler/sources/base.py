# coding=utf-8
"""
爬虫源基础模块

提供源注册机制和通用 HTTP 请求工具。
每个数据源通过 @source_fetcher("source_id") 装饰器注册。
"""

import logging
import re
from typing import Any, Callable, Coroutine, Dict, List, Optional

import requests

# 检测可用的 HTML 解析器
try:
    import lxml  # noqa: F401
    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

logger = logging.getLogger("trendradar.crawler.sources")

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# 全局请求会话
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """获取全局复用的请求会话"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(DEFAULT_HEADERS)
    return _session


def fetch(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
    response_type: str = "auto",
) -> Any:
    """
    通用 HTTP GET 请求

    Args:
        url: 请求 URL
        headers: 额外请求头（会与默认头合并）
        params: URL 查询参数
        timeout: 超时秒数
        response_type: 响应类型 - "json" / "text" / "bytes" / "auto"

    Returns:
        解析后的响应数据
    """
    session = get_session()
    resp = session.get(url, headers=headers, params=params, timeout=timeout)
    resp.raise_for_status()

    if response_type == "json":
        return resp.json()
    elif response_type == "text":
        return resp.text
    elif response_type == "bytes":
        return resp.content
    elif response_type == "auto":
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return resp.json()
        return resp.text
    return resp.text


def fetch_raw(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> requests.Response:
    """获取原始 Response 对象（用于获取 Cookie 等）"""
    session = get_session()
    return session.get(url, headers=headers, timeout=timeout)


# ============================================================
# 源注册系统
# ============================================================

# 源爬虫函数签名: () -> List[Dict]
# 每个 Dict 至少包含 {"title": str, "url": str}，可选 {"id": str, "mobileUrl": str, "pubDate": int, "extra": dict}
SourceFetcherFn = Callable[[], List[Dict[str, Any]]]


class SourceRegistry:
    """数据源注册表"""

    _registry: Dict[str, SourceFetcherFn] = {}

    @classmethod
    def register(cls, source_id: str, fn: SourceFetcherFn) -> None:
        """注册一个数据源"""
        cls._registry[source_id] = fn
        logger.debug(f"已注册数据源: {source_id}")

    @classmethod
    def get(cls, source_id: str) -> Optional[SourceFetcherFn]:
        """获取指定源的抓取函数"""
        return cls._registry.get(source_id)

    @classmethod
    def get_all_ids(cls) -> List[str]:
        """获取所有已注册的源 ID"""
        return list(cls._registry.keys())

    @classmethod
    def has(cls, source_id: str) -> bool:
        """检查源是否已注册"""
        return source_id in cls._registry

    @classmethod
    def fetch(cls, source_id: str) -> List[Dict[str, Any]]:
        """执行指定源的抓取"""
        fn = cls._registry.get(source_id)
        if fn is None:
            raise ValueError(f"未注册的数据源: {source_id}")
        return fn()


def source_fetcher(*source_ids: str):
    """
    数据源注册装饰器

    用法:
        @source_fetcher("weibo")
        def fetch_weibo():
            ...

        # 多个源 ID 共享同一个爬虫
        @source_fetcher("wallstreetcn", "wallstreetcn-quick")
        def fetch_wallstreetcn_live():
            ...
    """
    def decorator(fn: SourceFetcherFn) -> SourceFetcherFn:
        for sid in source_ids:
            SourceRegistry.register(sid, fn)
        return fn
    return decorator


def register_sources(source_map: Dict[str, SourceFetcherFn]) -> None:
    """批量注册源（用于一个文件导出多个源）"""
    for sid, fn in source_map.items():
        SourceRegistry.register(sid, fn)
