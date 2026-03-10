# coding=utf-8
"""哔哩哔哩热搜 - API JSON"""

from urllib.parse import quote

from .base import register_sources, fetch


def _fetch_bilibili_hot_search():
    url = "https://s.search.bilibili.com/main/hotword?limit=30"
    res = fetch(url, response_type="json")
    items = res.get("list", [])
    return [
        {
            "id": item["keyword"],
            "title": item["show_name"],
            "url": f"https://search.bilibili.com/all?keyword={quote(item['keyword'])}",
            "extra": {
                "icon": item.get("icon"),
            },
        }
        for item in items
        if item.get("keyword")
    ]


register_sources({
    "bilibili": _fetch_bilibili_hot_search,
    "bilibili-hot-search": _fetch_bilibili_hot_search,
})
