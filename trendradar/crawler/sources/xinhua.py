# coding=utf-8
"""新华网 - HTML Scraping"""

from bs4 import BeautifulSoup

from .base import source_fetcher, fetch, HTML_PARSER


@source_fetcher("xinhua")
def fetch_xinhua():
    html = fetch(
        "http://www.news.cn/politics/",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        response_type="text",
    )
    soup = BeautifulSoup(html, HTML_PARSER)
    news = []
    seen_urls = set()

    # 策略1：主新闻列表（多种选择器兼容不同时期页面结构）
    selectors = [
        ".xpage-content-list .column-center-item .tit span a",
        ".xpage-content-list .column-center-item a",
        ".xpage-content-list a[href]",
        "ul.dataList li a",
        ".domPC ul li a",
    ]
    for sel in selectors:
        for a in soup.select(sel):
            title = a.get_text(strip=True)
            href = str(a.get("href", ""))

            if title and href and len(title) > 4 and "/c.html" in href:
                url = href if href.startswith("http") else f"https://www.news.cn{href}"
                if url not in seen_urls:
                    seen_urls.add(url)
                    news.append({
                        "id": url,
                        "title": title,
                        "url": url,
                    })
        if news:
            break

    # 策略2：备用 - 扫描所有含 news.cn 的文章页链接
    if not news:
        for a in soup.select("a[href]"):
            href = str(a.get("href", ""))
            title = str(a.get("title", "")) or a.get_text(strip=True)

            if (title and len(title) > 6
                    and "news.cn" in href
                    and "/c.html" in href
                    and "rss" not in href
                    and "index.htm" not in href):
                url = href if href.startswith("http") else f"https://www.news.cn{href}"
                if url not in seen_urls:
                    seen_urls.add(url)
                    news.append({
                        "id": url,
                        "title": title,
                        "url": url,
                    })

    return news
