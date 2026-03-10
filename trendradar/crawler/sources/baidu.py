# coding=utf-8
"""百度热搜 - HTML 内嵌 SSR JSON"""

import json
import re

from .base import source_fetcher, fetch


@source_fetcher("baidu")
def fetch_baidu():
    raw = fetch("https://top.baidu.com/board?tab=realtime", response_type="text")

    # 从 HTML 注释中提取 SSR JSON: <!--s-data:{...}-->
    match = re.search(r"<!--s-data:(.*?)-->", raw, re.DOTALL)
    if not match:
        raise ValueError("无法从百度热搜页面提取数据")

    data = json.loads(match.group(1))
    cards = data.get("data", {}).get("cards", [])
    if not cards:
        return []

    items = cards[0].get("content", [])
    return [
        {
            "id": item["rawUrl"],
            "title": item["word"],
            "url": item["rawUrl"],
            "extra": {
                "hover": item.get("desc", ""),
            },
        }
        for item in items
        if not item.get("isTop") and item.get("word")
    ]
