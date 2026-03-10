# coding=utf-8
"""百度贴吧热议 - API JSON"""

from .base import source_fetcher, fetch


@source_fetcher("tieba")
def fetch_tieba():
    url = "https://tieba.baidu.com/hottopic/browse/topicList"
    res = fetch(url, response_type="json")
    items = res.get("data", {}).get("bang_topic", {}).get("topic_list", [])
    return [
        {
            "id": item["topic_id"],
            "title": item["topic_name"],
            "url": item.get("topic_url", ""),
        }
        for item in items
        if item.get("topic_name")
    ]
