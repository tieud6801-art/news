# coding=utf-8
"""东方财富 7×24 快讯 - JSONP 格式"""

from datetime import datetime

import pytz

from .base import source_fetcher, fetch
from .utils import parse_jsonp


@source_fetcher("eastmoney")
def fetch_eastmoney(context=None):
    max_pages = context.max_pages if context else 1

    news = []
    seen_keys = set()
    for page in range(1, max_pages + 1):
        raw = fetch(
            f"https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_{page}_.html",
            response_type="text",
        )
        raw = raw.strip().lstrip('\ufeff')
        data = parse_jsonp(raw, "ajaxResult")
        items = data.get("LivesList", [])
        if not items:
            break

        page_has_crawl_date = False
        page_has_before_crawl_date = False

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
                    parsed_time = datetime.strptime(item["showtime"], "%Y-%m-%d %H:%M:%S")
                    pub_date = int(pytz.timezone("Asia/Shanghai").localize(parsed_time).timestamp() * 1000)
                except (ValueError, TypeError):
                    pass

            if context:
                if context.is_crawl_date_timestamp_ms(pub_date):
                    page_has_crawl_date = True
                elif context.is_before_crawl_date_timestamp_ms(pub_date):
                    page_has_before_crawl_date = True
                    continue

            key = url or title
            if key in seen_keys:
                continue
            seen_keys.add(key)

            news.append({
                "id": str(news_id),
                "title": title,
                "url": url,
                "pubDate": pub_date,
            })

        if not context:
            break
        if page_has_before_crawl_date or not page_has_crawl_date:
            break

    return news
