# coding=utf-8
"""稀土掘金 - API JSON"""

from .base import source_fetcher, fetch


@source_fetcher("juejin")
def fetch_juejin():
    url = "https://api.juejin.cn/content_api/v1/content/article_rank?category_id=1&type=hot&spider=0"
    res = fetch(url, response_type="json")
    return [
        {
            "id": item["content"]["content_id"],
            "title": item["content"]["title"],
            "url": f"https://juejin.cn/post/{item['content']['content_id']}",
        }
        for item in res.get("data", [])
        if item.get("content", {}).get("title")
    ]
