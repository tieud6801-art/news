# coding=utf-8
"""凤凰网 - HTML 内嵌 JS 变量"""

import json
import re

from .base import source_fetcher, fetch


@source_fetcher("ifeng")
def fetch_ifeng():
    html = fetch("https://www.ifeng.com/", response_type="text")

    match = re.search(r"var\s+allData\s*=\s*(\{[\s\S]*?\});", html)
    if not match:
        return []

    data = json.loads(match.group(1))
    items = data.get("hotNews1", [])

    return [
        {
            "id": item["url"],
            "title": item["title"],
            "url": item["url"],
            "extra": {
                "date": item.get("newsTime"),
            },
        }
        for item in items
        if item.get("title") and item.get("url")
    ]
