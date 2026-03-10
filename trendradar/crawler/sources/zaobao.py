# coding=utf-8
"""联合早报 - HTML Scraping（GB2312 编码）"""

import requests
from bs4 import BeautifulSoup

from .base import source_fetcher, HTML_PARSER
from .utils import parse_relative_date


@source_fetcher("zaobao")
def fetch_zaobao():
    base_url = "https://www.zaochenbao.com"

    # GB2312 编码页面，需要以 bytes 方式获取后解码
    resp = requests.get(
        f"{base_url}/realtime/",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        timeout=15,
    )
    resp.raise_for_status()

    # 尝试 GB2312 解码，失败则回退到 GBK
    try:
        html = resp.content.decode("gb2312")
    except (UnicodeDecodeError, LookupError):
        html = resp.content.decode("gbk", errors="replace")

    soup = BeautifulSoup(html, HTML_PARSER)
    items = soup.select("div.list-block > a.item")
    news = []

    for a in items:
        href = str(a.get("href", ""))
        title_el = a.select_one(".eps")
        title = title_el.get_text(strip=True) if title_el else ""

        date_el = a.select_one(".pdt10")
        date_str = date_el.get_text(strip=True) if date_el else ""
        # 处理 "- " 为 " "
        date_str = date_str.replace("- ", " ").replace("-\xa0", " ")

        if not href or not title or not date_str:
            continue

        pub_date = parse_relative_date(date_str, "Asia/Shanghai")
        news.append({
            "id": href,
            "title": title,
            "url": base_url + href,
            "pubDate": int(pub_date.timestamp() * 1000),
        })

    news.sort(key=lambda x: x.get("pubDate", 0), reverse=True)
    return news
