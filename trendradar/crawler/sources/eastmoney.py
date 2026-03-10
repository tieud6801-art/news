# coding=utf-8
"""东方财富 7×24 快讯 - JSONP 格式"""

from datetime import datetime

from .base import source_fetcher, fetch
from .utils import parse_jsonp


@source_fetcher("eastmoney")
def fetch_eastmoney():
    raw = fetch(
        "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html",
        response_type="text",
    )
    raw = raw.strip().lstrip('\ufeff')
    data = parse_jsonp(raw, "ajaxResult")
    items = data.get("LivesList", [])

    news = []
    for item in items:
        title = item.get("title", "")
        if not title:
            continue

        news_id = item.get("newsid") or item.get("id", "")
        url = (
            item.get("url_unique")
            or item.get("url_w")
            or f"https://finance.eastmoney.com/a/{news_id}.html"
        )

        pub_date = None
        if item.get("showtime"):
            try:
                pub_date = int(datetime.strptime(
                    item["showtime"], "%Y-%m-%d %H:%M:%S"
                ).timestamp() * 1000)
            except (ValueError, TypeError):
                pass

        news.append({
            "id": str(news_id),
            "title": title,
            "url": url,
            "pubDate": pub_date,
        })

    return news
