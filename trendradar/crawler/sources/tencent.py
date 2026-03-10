# coding=utf-8
"""腾讯新闻 - API JSON"""

from .base import source_fetcher, fetch


@source_fetcher("tencent-hot")
def fetch_tencent_hot():
    url = "https://i.news.qq.com/web_backend/v2/getTagInfo?tagId=aEWqxLtdgmQ%3D"
    res = fetch(
        url,
        headers={"Referer": "https://news.qq.com/"},
        response_type="json",
    )
    articles = res.get("data", {}).get("tabs", [{}])[0].get("articleList", [])
    return [
        {
            "id": item.get("id", ""),
            "title": item["title"],
            "url": item.get("link_info", {}).get("url", ""),
            "extra": {
                "hover": item.get("desc", ""),
            },
        }
        for item in articles
        if item.get("title")
    ]
