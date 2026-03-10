# coding=utf-8
"""华尔街见闻 - API JSON（4个子源）"""

from .base import register_sources, fetch


def _fetch_wallstreetcn_live():
    """快讯"""
    url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"
    res = fetch(url, response_type="json")
    items = res.get("data", {}).get("items", [])
    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title") or item.get("content_text", ""),
            "url": item.get("uri", ""),
            "extra": {
                "date": item.get("display_time", 0) * 1000,
            },
        }
        for item in items
        if item.get("title") or item.get("content_text")
    ]


def _fetch_wallstreetcn_news():
    """资讯"""
    url = "https://api-one.wallstcn.com/apiv1/content/information-flow?channel=global-channel&accept=article&limit=30"
    res = fetch(url, response_type="json")
    items = res.get("data", {}).get("items", [])
    return [
        {
            "id": str(h.get("id", "")),
            "title": h.get("title") or h.get("content_short", ""),
            "url": h.get("uri", ""),
            "extra": {
                "date": h.get("display_time", 0) * 1000,
            },
        }
        for item in items
        if item.get("resource_type") not in ("theme", "ad")
        and item.get("resource", {}).get("type") != "live"
        and item.get("resource", {}).get("uri")
        for h in [item["resource"]]
    ]


def _fetch_wallstreetcn_hot():
    """热门"""
    url = "https://api-one.wallstcn.com/apiv1/content/articles/hot?period=all"
    res = fetch(url, response_type="json")
    items = res.get("data", {}).get("day_items", [])
    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title", ""),
            "url": item.get("uri", ""),
        }
        for item in items
        if item.get("title")
    ]


register_sources({
    "wallstreetcn": _fetch_wallstreetcn_live,
    "wallstreetcn-quick": _fetch_wallstreetcn_live,
    "wallstreetcn-news": _fetch_wallstreetcn_news,
    "wallstreetcn-hot": _fetch_wallstreetcn_hot,
})
