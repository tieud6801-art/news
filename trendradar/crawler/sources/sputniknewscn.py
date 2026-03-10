# coding=utf-8
"""俄罗斯卫星通讯社中文 - HTML Scraping + 代理回退"""

import logging

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER

logger = logging.getLogger(__name__)

# 代理回退 URL
_PROXY_URL = "https://newsnow-omega-one.vercel.app/api/s?id=sputniknewscn&latest="


def _fetch_direct():
    """直接抓取"""
    html = fetch("https://sputniknews.cn/services/widget/lenta/", response_type="text")
    soup = BeautifulSoup(html, HTML_PARSER)

    items = soup.select(".lenta__item")
    news = []

    for item in items:
        a = item.select_one("a")
        if not a:
            continue

        href = str(a.get("href", ""))
        title_el = a.select_one(".lenta__item-text")
        title = title_el.get_text(strip=True) if title_el else ""

        date_el = a.select_one(".lenta__item-date")
        unix_time = str(date_el.get("data-unixtime", "")) if date_el else ""

        if not href or not title or not unix_time:
            continue

        # Unix 时间戳为 10 位，需补 000 转毫秒
        try:
            timestamp = int(f"{unix_time}000")
        except (ValueError, TypeError):
            timestamp = 0

        news.append({
            "id": href,
            "title": title,
            "url": f"https://sputniknews.cn{href}",
            "extra": {
                "date": timestamp,
            },
        })

    return news


def _fetch_via_proxy():
    """通过代理回退获取"""
    try:
        data = fetch(_PROXY_URL, response_type="json")
        return data.get("items", [])
    except Exception as e:
        logger.warning(f"代理获取 sputniknewscn 也失败: {e}")
        return []


@source_fetcher("sputniknewscn")
def fetch_sputniknewscn():
    try:
        result = _fetch_direct()
        if result:
            return result
    except Exception as e:
        logger.warning(f"直连 sputniknewscn 失败: {e}, 尝试代理...")

    return _fetch_via_proxy()
