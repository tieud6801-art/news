# coding=utf-8
"""IT之家 - HTML Scraping"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, get_session, HTML_PARSER
from .utils import parse_relative_date

# 广告关键词
_AD_KEYWORDS = {"神券", "优惠", "补贴", "京东"}


@source_fetcher("ithome")
def fetch_ithome(context=None):
    html = fetch("https://www.ithome.com/list/", response_type="text")
    news = []
    seen_keys = set()

    page_news, page_has_crawl_date, page_has_before_crawl_date = _parse_ithome_items(
        html, context, seen_keys
    )
    news.extend(page_news)

    if not context or page_has_before_crawl_date or not page_has_crawl_date:
        return news

    session = get_session()
    for page in range(2, context.max_pages + 1):
        resp = session.post(
            f"https://www.ithome.com/category/listpage?page={page}",
            headers={"Referer": "https://www.ithome.com/list/"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        page_html = (data.get("content") or {}).get("html", "")
        if not page_html:
            break

        page_news, page_has_crawl_date, page_has_before_crawl_date = _parse_ithome_items(
            page_html, context, seen_keys
        )
        news.extend(page_news)
        if page_has_before_crawl_date or not page_has_crawl_date:
            break

    return news


def _parse_ithome_items(html, context=None, seen_keys=None):
    if seen_keys is None:
        seen_keys = set()
    soup = BeautifulSoup(html, HTML_PARSER)

    items = soup.select("#list > div.fl > ul > li") or soup.select("li")
    news = []
    page_has_crawl_date = False
    page_has_before_crawl_date = False

    for item in items:
        a = item.select_one("a.t") or item.select_one("a.c")
        date_el = item.select_one("i")

        if not a or not date_el:
            continue

        url = a.get("href", "")
        title = a.get_text(strip=True)
        date_str = date_el.get_text(strip=True)

        if not url or not title or not date_str:
            continue

        # 过滤广告
        if "lapin" in url:
            continue
        if any(kw in title for kw in _AD_KEYWORDS):
            continue

        pub_date = parse_relative_date(date_str, "Asia/Shanghai")
        pub_date_ms = int(pub_date.timestamp() * 1000)
        if context:
            if context.is_crawl_date_timestamp_ms(pub_date_ms):
                page_has_crawl_date = True
            elif context.is_before_crawl_date_timestamp_ms(pub_date_ms):
                page_has_before_crawl_date = True
                continue

        key = url or title
        if key in seen_keys:
            continue
        seen_keys.add(key)

        news.append({
            "id": url,
            "title": title,
            "url": url,
            "pubDate": pub_date_ms,
        })

    # 按时间倒序
    news.sort(key=lambda x: x.get("pubDate", 0), reverse=True)
    return news, page_has_crawl_date, page_has_before_crawl_date
