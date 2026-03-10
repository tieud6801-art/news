# coding=utf-8
"""少数派 - API JSON"""

import time

from .base import source_fetcher, fetch


@source_fetcher("sspai")
def fetch_sspai():
    timestamp = int(time.time() * 1000)
    url = (
        f"https://sspai.com/api/v1/article/tag/page/get"
        f"?limit=30&offset=0&created_at={timestamp}"
        f"&tag=%E7%83%AD%E9%97%A8%E6%96%87%E7%AB%A0&released=false"
    )
    res = fetch(url, response_type="json")
    return [
        {
            "id": str(item["id"]),
            "title": item["title"],
            "url": f"https://sspai.com/post/{item['id']}",
        }
        for item in res.get("data", [])
        if item.get("title")
    ]
