# coding=utf-8
"""靠谱新闻 - API JSON (Azure Blob)"""

import logging

from .base import source_fetcher, fetch

# 过滤掉的发布者
_FILTERED_PUBLISHERS = {"财新", "公视"}
logger = logging.getLogger(__name__)


@source_fetcher("kaopu")
def fetch_kaopu():
    url = "https://kaopustorage.blob.core.windows.net/news-prod/news_list_hans_0.json"
    try:
        res = fetch(url, response_type="json")
    except Exception as exc:
        logger.warning(f"直连 kaopu 失败，尝试 NewsNow 备用源: {exc}")
        fallback = fetch("https://newsnow.busiyi.world/api/s?id=kaopu&latest", response_type="json")
        res = fallback.get("items", [])

    return [
        {
            "id": item.get("link") or item.get("url", ""),
            "title": item["title"],
            "url": item.get("link") or item.get("url", ""),
            "pubDate": item.get("pub_date"),
            "extra": {
                "hover": item.get("description", ""),
                "info": item.get("publisher", ""),
            },
        }
        for item in res
        if item.get("title") and item.get("publisher") not in _FILTERED_PUBLISHERS
    ]
