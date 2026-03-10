# coding=utf-8
"""IT之家 - HTML Scraping"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER
from .utils import parse_relative_date

# 广告关键词
_AD_KEYWORDS = {"神券", "优惠", "补贴", "京东"}


@source_fetcher("ithome")
def fetch_ithome():
    html = fetch("https://www.ithome.com/list/", response_type="text")
    soup = BeautifulSoup(html, HTML_PARSER)

    items = soup.select("#list > div.fl > ul > li")
    news = []

    for item in items:
        a = item.select_one("a.t")
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
        news.append({
            "id": url,
            "title": title,
            "url": url,
            "pubDate": int(pub_date.timestamp() * 1000),
        })

    # 按时间倒序
    news.sort(key=lambda x: x.get("pubDate", 0), reverse=True)
    return news
