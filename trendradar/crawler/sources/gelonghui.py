# coding=utf-8
"""格隆汇 - API JSON + HTML fallback"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER
from .utils import parse_relative_date


@source_fetcher("gelonghui")
def fetch_gelonghui(context=None):
    if context:
        api_news = _fetch_gelonghui_api(context)
        if api_news:
            return api_news
    return _fetch_gelonghui_html()


def _fetch_gelonghui_api(context):
    news = []
    seen_keys = set()
    cursor = ""

    for _ in range(context.max_pages):
        res = fetch(
            "https://www.gelonghui.com/api/news/filter/list",
            params={"createDate": cursor, "count": 20},
            headers={"Referer": "https://www.gelonghui.com/news/"},
            response_type="json",
        )
        items = res.get("result", [])
        if not items:
            break

        page_has_crawl_date = False
        page_has_before_crawl_date = False
        next_cursor = cursor

        for item in items:
            title = item.get("title", "")
            news_id = item.get("id", "")
            create_date = item.get("createDate")
            if not title or not news_id or not create_date:
                continue

            timestamp_ms = int(create_date) * 1000
            next_cursor = str(create_date)

            if context.is_crawl_date_timestamp_ms(timestamp_ms):
                page_has_crawl_date = True
            elif context.is_before_crawl_date_timestamp_ms(timestamp_ms):
                page_has_before_crawl_date = True
                continue

            url = f"https://www.gelonghui.com/news/{news_id}"
            key = url or title
            if key in seen_keys:
                continue
            seen_keys.add(key)

            news.append({
                "id": str(news_id),
                "title": title,
                "url": url,
                "extra": {
                    "date": timestamp_ms,
                    "info": item.get("typeName", ""),
                    "hover": item.get("content", ""),
                },
            })

        if page_has_before_crawl_date or not page_has_crawl_date or next_cursor == cursor:
            break
        cursor = next_cursor

    return news


def _fetch_gelonghui_html():
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
