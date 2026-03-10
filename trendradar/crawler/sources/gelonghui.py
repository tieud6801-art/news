# coding=utf-8
"""格隆汇 - HTML Scraping"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER
from .utils import parse_relative_date


@source_fetcher("gelonghui")
def fetch_gelonghui():
    base_url = "https://www.gelonghui.com"
    html = fetch(f"{base_url}/news/", response_type="text")
    soup = BeautifulSoup(html, HTML_PARSER)

    items = soup.select(".article-content")
    news = []

    for item in items:
        a = item.select_one(".detail-right > a")
        if not a:
            continue

        href = str(a.get("href", ""))
        title_el = a.select_one("h2")
        title = title_el.get_text(strip=True) if title_el else ""

        # 来源信息
        info_el = item.select_one(".time > span:nth-child(1)")
        info = info_el.get_text(strip=True) if info_el else ""

        # 相对时间
        time_el = item.select_one(".time > span:nth-child(3)")
        relative_time = time_el.get_text(strip=True) if time_el else ""

        if not href or not title or not relative_time:
            continue

        pub_date = parse_relative_date(relative_time, "Asia/Shanghai")
        news.append({
            "id": href,
            "title": title,
            "url": base_url + href,
            "extra": {
                "date": int(pub_date.timestamp() * 1000),
                "info": info,
            },
        })

    return news
