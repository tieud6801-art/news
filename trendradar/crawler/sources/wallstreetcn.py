# coding=utf-8
"""华尔街见闻 - API JSON（4个子源）"""

from .base import register_sources, fetch


def _include_by_context(news_item, timestamp_ms, context, seen_keys):
    if context:
        if context.is_before_crawl_date_timestamp_ms(timestamp_ms):
            return False, False, True
        if not context.is_crawl_date_timestamp_ms(timestamp_ms):
            return False, False, False

    key = news_item.get("url") or news_item.get("id") or news_item.get("title")
    if key in seen_keys:
        return False, bool(context), False
    seen_keys.add(key)
    return True, bool(context), False


def _fetch_wallstreetcn_live(context=None):
    """快讯"""
    base_url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"
    news = []
    seen_keys = set()
    cursor = None
    max_pages = context.max_pages if context else 1

    for _ in range(max_pages):
        url = base_url + (f"&cursor={cursor}" if cursor else "")
        res = fetch(url, response_type="json")
        data = res.get("data", {})
        items = data.get("items", [])
        if not items:
            break

        page_has_crawl_date = False
        page_has_before_crawl_date = False
        for item in items:
            if not (item.get("title") or item.get("content_text")):
                continue
            timestamp_ms = item.get("display_time", 0) * 1000
            news_item = {
                "id": str(item.get("id", "")),
                "title": item.get("title") or item.get("content_text", ""),
                "url": item.get("uri", ""),
                "extra": {
                    "date": timestamp_ms,
                },
            }
            include, is_crawl_date, is_before = _include_by_context(
                news_item, timestamp_ms, context, seen_keys
            )
            page_has_crawl_date = page_has_crawl_date or is_crawl_date
            page_has_before_crawl_date = page_has_before_crawl_date or is_before
            if include:
                news.append(news_item)

        cursor = data.get("next_cursor")
        if not context or not cursor:
            break
        if page_has_before_crawl_date or not page_has_crawl_date:
            break

    return news


def _fetch_wallstreetcn_news(context=None):
    """资讯"""
    base_url = "https://api-one.wallstcn.com/apiv1/content/information-flow?channel=global-channel&accept=article&limit=30"
    news = []
    seen_keys = set()
    cursor = None
    max_pages = context.max_pages if context else 1

    for _ in range(max_pages):
        url = base_url + (f"&cursor={cursor}" if cursor else "")
        res = fetch(url, response_type="json")
        data = res.get("data", {})
        items = data.get("items", [])
        if not items:
            break

        page_has_crawl_date = False
        page_has_before_crawl_date = False
        for item in items:
            if (
                item.get("resource_type") in ("theme", "ad")
                or item.get("resource", {}).get("type") == "live"
                or not item.get("resource", {}).get("uri")
            ):
                continue
            h = item["resource"]
            timestamp_ms = h.get("display_time", 0) * 1000
            news_item = {
                "id": str(h.get("id", "")),
                "title": h.get("title") or h.get("content_short", ""),
                "url": h.get("uri", ""),
                "extra": {
                    "date": timestamp_ms,
                },
            }
            include, is_crawl_date, is_before = _include_by_context(
                news_item, timestamp_ms, context, seen_keys
            )
            page_has_crawl_date = page_has_crawl_date or is_crawl_date
            page_has_before_crawl_date = page_has_before_crawl_date or is_before
            if include:
                news.append(news_item)

        cursor = data.get("next_cursor")
        if not context or not cursor:
            break
        if page_has_before_crawl_date or not page_has_crawl_date:
            break

    return news


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
