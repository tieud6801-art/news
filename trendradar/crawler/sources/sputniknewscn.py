# coding=utf-8
"""俄罗斯卫星通讯社中文 - HTML Scraping + 代理回退"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER

logger = logging.getLogger(__name__)

# 代理回退 URL
_PROXY_URL = "https://newsnow-omega-one.vercel.app/api/s?id=sputniknewscn&latest="


def _fetch_direct(context=None):
    """直接抓取"""
    base_url = "https://sputniknews.cn"
    url = f"{base_url}/services/widget/lenta/"
    news = []
    seen_keys = set()

    max_pages = context.max_pages if context else 1
    for _ in range(max_pages):
        html = fetch(url, response_type="text")
        page_news, next_url, page_has_crawl_date, page_has_before_crawl_date = _parse_lenta_page(
            html, base_url, context, seen_keys
        )
        news.extend(page_news)

        if not context or not next_url:
            break
        if page_has_before_crawl_date or not page_has_crawl_date:
            break
        url = urljoin(base_url, next_url)

    return news


def _parse_lenta_page(html, base_url, context=None, seen_keys=None):
    if seen_keys is None:
        seen_keys = set()
    soup = BeautifulSoup(html, HTML_PARSER)

    items = soup.select(".lenta__item")
    news = []
    page_has_crawl_date = False
    page_has_before_crawl_date = False

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

        if context:
            if context.is_crawl_date_timestamp_ms(timestamp):
                page_has_crawl_date = True
            elif context.is_before_crawl_date_timestamp_ms(timestamp):
                page_has_before_crawl_date = True
                continue

        url = f"{base_url}{href}"
        key = url or title
        if key in seen_keys:
            continue
        seen_keys.add(key)

        news.append({
            "id": href,
            "title": title,
            "url": url,
            "extra": {
                "date": timestamp,
            },
        })

    next_link = soup.select_one('[data-next*="more.html"]')
    next_url = str(next_link.get("data-next", "")) if next_link else ""
    return news, next_url, page_has_crawl_date, page_has_before_crawl_date


def _fetch_via_proxy():
    """通过代理回退获取"""
    try:
        data = fetch(_PROXY_URL, response_type="json")
        return data.get("items", [])
    except Exception as e:
        logger.warning(f"代理获取 sputniknewscn 也失败: {e}")
        return []


@source_fetcher("sputniknewscn")
def fetch_sputniknewscn(context=None):
    try:
        result = _fetch_direct(context)
        if result:
            return result
    except Exception as e:
        logger.warning(f"直连 sputniknewscn 失败: {e}, 尝试代理...")

    return _fetch_via_proxy()
