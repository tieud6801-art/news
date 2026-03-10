# coding=utf-8
"""靠谱新闻 - API JSON (Azure Blob)"""

from .base import source_fetcher, fetch

# 过滤掉的发布者
_FILTERED_PUBLISHERS = {"财新", "公视"}


@source_fetcher("kaopu")
def fetch_kaopu():
    url = "https://kaopustorage.blob.core.windows.net/news-prod/news_list_hans_0.json"
    res = fetch(url, response_type="json")
    return [
        {
            "id": item["link"],
            "title": item["title"],
            "url": item["link"],
            "pubDate": item.get("pub_date"),
            "extra": {
                "hover": item.get("description", ""),
                "info": item.get("publisher", ""),
            },
        }
        for item in res
        if item.get("title") and item.get("publisher") not in _FILTERED_PUBLISHERS
    ]
