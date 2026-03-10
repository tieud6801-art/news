# coding=utf-8
"""知乎热榜 - API JSON"""

import re

from .base import source_fetcher, fetch


@source_fetcher("zhihu")
def fetch_zhihu():
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=20&desktop=true"
    res = fetch(url, response_type="json")
    items = res.get("data", [])
    return [
        {
            "id": (re.search(r"(\d+)$", item["target"]["link"]["url"]) or [None, item["target"]["link"]["url"]])[1],
            "title": item["target"]["title_area"]["text"],
            "url": item["target"]["link"]["url"],
            "extra": {
                "info": item["target"].get("metrics_area", {}).get("text", ""),
                "hover": item["target"].get("excerpt_area", {}).get("text", ""),
            },
        }
        for item in items
        if item.get("target", {}).get("title_area", {}).get("text")
    ]
