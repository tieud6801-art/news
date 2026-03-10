# coding=utf-8
"""MKTNews 市场快讯 - API JSON"""

import re

from .base import source_fetcher, fetch, register_sources


def _fetch_mktnews_flash():
    url = "https://api.mktnews.net/api/flash?type=0&limit=50"
    res = fetch(url, response_type="json")
    items = res.get("data", [])

    # 按时间倒序
    items.sort(key=lambda x: x.get("time", ""), reverse=True)

    results = []
    for item in items:
        content = item.get("data", {}).get("content", "")
        title = item.get("data", {}).get("title", "")

        # 如果没有 title，尝试从 content 的 【标题】 格式提取
        if not title:
            match = re.match(r"^【([^】]*)】(.*)$", content)
            title = match.group(1) if match else content

        if not title:
            continue

        results.append({
            "id": item.get("id", ""),
            "title": title,
            "url": f"https://mktnews.net/flashDetail.html?id={item.get('id', '')}",
            "pubDate": item.get("time"),
            "extra": {
                "info": "Important" if item.get("important") == 1 else None,
                "hover": content,
            },
        })

    return results


register_sources({
    "mktnews": _fetch_mktnews_flash,
    "mktnews-flash": _fetch_mktnews_flash,
})
