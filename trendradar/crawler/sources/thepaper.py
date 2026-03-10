# coding=utf-8
"""澎湃新闻 - API JSON"""

from .base import source_fetcher, fetch


@source_fetcher("thepaper")
def fetch_thepaper():
    url = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
    res = fetch(url, response_type="json")
    items = res.get("data", {}).get("hotNews", [])
    return [
        {
            "id": item["contId"],
            "title": item["name"],
            "url": f"https://www.thepaper.cn/newsDetail_forward_{item['contId']}",
            "mobileUrl": f"https://m.thepaper.cn/newsDetail_forward_{item['contId']}",
        }
        for item in items
        if item.get("name")
    ]
