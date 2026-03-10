# coding=utf-8
"""雪球 - API JSON（需动态 Cookie）"""

import re

import requests

from .base import register_sources, fetch, DEFAULT_HEADERS


def _get_xueqiu_cookie() -> str:
    """使用独立 Session 请求雪球首页获取完整 Cookie（避免全局 Session Cookie 污染）"""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    resp = session.get("https://xueqiu.com/hq", timeout=15)
    resp.raise_for_status()
    return "; ".join(f"{k}={v}" for k, v in session.cookies.items())


def _fetch_xueqiu_hotstock():
    """热股榜"""
    url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json?size=30&_type=10&type=10"
    cookie = _get_xueqiu_cookie()
    res = fetch(
        url,
        headers={"cookie": cookie},
        response_type="json",
    )
    items = res.get("data", {}).get("items", [])
    return [
        {
            "id": item["code"],
            "title": item["name"],
            "url": f"https://xueqiu.com/s/{item['code']}",
            "extra": {
                "info": f"{item.get('percent', '')}% {item.get('exchange', '')}",
            },
        }
        for item in items
        if not item.get("ad") and item.get("name")
    ]


def _fetch_xueqiu_news():
    """快讯"""
    url = "https://xueqiu.com/statuses/livenews/list.json?since_id=-1&max_id=-1&count=30"
    cookie = _get_xueqiu_cookie()
    res = fetch(
        url,
        headers={
            "cookie": cookie,
            "referer": "https://xueqiu.com/",
            "origin": "https://xueqiu.com",
            "x-requested-with": "XMLHttpRequest",
        },
        response_type="json",
    )
    items = res.get("items", [])
    news = []
    for item in items:
        text = item.get("text", "")
        # 清理 HTML 标签和多余空白
        title = re.sub(r"<[^>]+>", "", text)
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue
        news.append({
            "id": str(item.get("id", "")),
            "title": title,
            "url": item.get("target") or "https://xueqiu.com",
            "pubDate": item.get("created_at"),
        })
    return news


register_sources({
    "xueqiu": _fetch_xueqiu_hotstock,
    "xueqiu-hotstock": _fetch_xueqiu_hotstock,
    "xueqiu-news": _fetch_xueqiu_news,
})
