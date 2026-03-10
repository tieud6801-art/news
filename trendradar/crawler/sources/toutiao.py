# coding=utf-8
"""今日头条 - API JSON"""

from .base import source_fetcher, fetch


@source_fetcher("toutiao")
def fetch_toutiao():
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    res = fetch(url, response_type="json")
    items = res.get("data", [])
    return [
        {
            "id": item["ClusterIdStr"],
            "title": item["Title"],
            "url": f"https://www.toutiao.com/trending/{item['ClusterIdStr']}/",
            "extra": {
                "icon": item.get("LabelUri", {}).get("url") if item.get("LabelUri") else None,
            },
        }
        for item in items
        if item.get("Title")
    ]
