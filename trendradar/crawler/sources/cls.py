# coding=utf-8
"""财联社 - API JSON + SHA-1/MD5 签名"""

import json

from .base import SourceCrawlContext, get_session, register_sources, fetch
from .utils import cls_get_search_params


def _fetch_cls_depth():
    """深度"""
    url = "https://www.cls.cn/v3/depth/home/assembled/1000"
    params = cls_get_search_params()
    res = fetch(url, params=params, response_type="json")

    items = res.get("data", {}).get("depth_list", [])
    # 按 ctime 倒序
    items.sort(key=lambda x: x.get("ctime", 0), reverse=True)

    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title") or item.get("brief", ""),
            "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
            "mobileUrl": item.get("shareurl", ""),
            "pubDate": item.get("ctime", 0) * 1000,
        }
        for item in items
        if item.get("title") or item.get("brief")
    ]


def _fetch_cls_hot():
    """热门"""
    url = "https://www.cls.cn/v2/article/hot/list"
    params = cls_get_search_params()
    res = fetch(url, params=params, response_type="json")

    items = res.get("data", [])
    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title") or item.get("brief", ""),
            "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
            "mobileUrl": item.get("shareurl", ""),
        }
        for item in items
        if item.get("title") or item.get("brief")
    ]


def _extract_next_data_assignment(html: str):
    marker = "__NEXT_DATA__ ="
    pos = html.find(marker)
    if pos < 0:
        return None

    start = html.find("{", pos)
    if start < 0:
        return None

    level = 0
    in_string = False
    escaped = False
    for idx, char in enumerate(html[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                return html[start:idx + 1]
    return None


def _fetch_cls_telegraph(context: SourceCrawlContext = None):
    """电报：RSSHub 路由不稳定，直接解析财联社移动端初始数据。"""
    url = "https://m.cls.cn/telegraph"
    session = get_session()
    response = session.get(url, timeout=15)
    response.raise_for_status()
    html = response.content.decode("utf-8", errors="ignore")

    data_text = _extract_next_data_assignment(html)
    if not data_text:
        return []

    data = json.loads(data_text)
    items = data.get("props", {}).get("initialState", {}).get("roll_data", [])
    news = []
    seen_keys = set()

    for item in items:
        article_id = str(item.get("id") or "").strip()
        timestamp_ms = int(item.get("ctime") or 0) * 1000
        title = (item.get("title") or item.get("brief") or item.get("content") or "").strip()
        if not title:
            continue
        detail_url = item.get("shareurl") or f"https://www.cls.cn/detail/{article_id}"
        news_item = {
            "id": article_id or detail_url,
            "title": title,
            "url": detail_url,
            "mobileUrl": item.get("shareurl", ""),
            "pubDate": timestamp_ms,
        }
        if context:
            if context.local_date_from_timestamp_ms(timestamp_ms) != context.crawl_date:
                continue
            if context.has_seen_item(news_item):
                continue
        key = news_item.get("url") or news_item.get("title")
        if key in seen_keys:
            continue
        seen_keys.add(key)
        news.append(news_item)

    return news


register_sources({
    "cls-depth": _fetch_cls_depth,
    "cls-hot": _fetch_cls_hot,
    "cls-telegraph": _fetch_cls_telegraph,
})
