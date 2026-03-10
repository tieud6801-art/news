# coding=utf-8
"""微博热搜 - HTML Scraping（需固定 Cookie）"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER

# 微博热搜固定 Cookie（绕过登录墙）
_WEIBO_COOKIE = "SUB=_2AkMWIuNSf8NxqwJRmP8dy2rhaoV2ygrEieKgfhKJJRMxHRl-yT9jqk86tRB6PaLNvQZR6zYUcYVT1zSjoSreQHidcUq7"


@source_fetcher("weibo")
def fetch_weibo():
    base_url = "https://s.weibo.com"
    url = f"{base_url}/top/summary?cate=realtimehot"

    html = fetch(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            ),
            "Cookie": _WEIBO_COOKIE,
            "referer": url,
        },
        response_type="text",
    )
    soup = BeautifulSoup(html, HTML_PARSER)

    rows = soup.select("#pl_top_realtimehot table tbody tr")[1:]  # 跳过第一行
    news = []

    flag_urls = {
        "新": "https://simg.s.weibo.com/moter/flags/1_0.png",
        "热": "https://simg.s.weibo.com/moter/flags/2_0.png",
        "爆": "https://simg.s.weibo.com/moter/flags/4_0.png",
    }

    for row in rows:
        links = row.select("td.td-02 a")
        link = None
        for a in links:
            href = str(a.get("href", ""))
            if href and "javascript:void(0)" not in href:
                link = a
                break

        if not link:
            continue

        title = link.get_text(strip=True)
        href = str(link.get("href", ""))

        if not title or not href:
            continue

        flag_el = row.select_one("td.td-03")
        flag = flag_el.get_text(strip=True) if flag_el else ""
        flag_url = flag_urls.get(flag)

        news.append({
            "id": title,
            "title": title,
            "url": f"{base_url}{href}",
            "mobileUrl": f"{base_url}{href}",
            "extra": {
                "icon": {"url": flag_url, "scale": 1.5} if flag_url else None,
            },
        })

    return news
