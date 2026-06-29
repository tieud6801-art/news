# coding=utf-8
"""Industry association and customs official sources."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

from .base import DEFAULT_HEADERS, HTML_PARSER, SourceCrawlContext, fetch_raw, register_sources


logger = logging.getLogger("trendradar.crawler.sources.industry_associations")
urllib3.disable_warnings(InsecureRequestWarning)

_TZ = "Asia/Shanghai"
_DATE_RE = re.compile(r"((?:19|20)\d{2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})")
_CN_DATE_RE = re.compile(r"((?:19|20)\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日?")
_MONTH_DAY_RE = re.compile(r"(?<![\d.])(\d{1,2})[-/](\d{1,2})(?![\d.])")
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)

_SOURCE_PAGES = {
    "customs-stats": {
        "url": "https://www.customs.gov.cn/customs/302249/zfxxgk/fdzdgknr/302274/index.html",
        "verify": False,
        "ignore_statuses": {412, 502, 504},
    },
    "cpia-news": {"url": "https://www.chinapv.org.cn/"},
    "caam-news": {"url": "http://www.caam.org.cn/chn/1/cate_2/list_1.html"},
    "sac-news": {"url": "https://www.sac.net.cn/xxgk/xhxx/gzdt/"},
    "crea-news": {"url": "http://www.fangchan.com/news/"},
    "iachina-news": {"url": "https://www.iachina.cn/col/col22/index.html"},
    "ceea-news": {"url": "http://ceea.org.cn/ceeacms/webTypeAction!manageView.do?typeId=201502034738000301703692746656"},
    "camet-news": {
        "url": "https://www.camet.org.cn/sy/xydt/",
        "mode": "camet_cards",
    },
    "isc-news": {"url": "https://www.isc.org.cn/category/7329.html"},
    "cpema-news": {"url": "https://www.cpema.org/index.php?m=content&c=index&a=lists&catid=27"},
}

_SKIP_TITLES = {
    "更多",
    "more",
    "more +",
    "查看更多",
    "查看详情",
    "查看详情 >>",
    "【详细】",
    "详细",
    "首页",
    "中文",
    "english",
}


def _today_local() -> datetime:
    return datetime.now(pytz.timezone(_TZ)).replace(hour=0, minute=0, second=0, microsecond=0)


def _fallback_year(context: Optional[SourceCrawlContext]) -> int:
    if context and context.crawl_date:
        return int(context.crawl_date[:4])
    return _today_local().year


def _normalize_date(text: str, fallback_year: int) -> str:
    text = text or ""
    match = _DATE_RE.search(text) or _CN_DATE_RE.search(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
    else:
        match = _MONTH_DAY_RE.search(text)
        if not match:
            return ""
        year = fallback_year
        month, day = (int(part) for part in match.groups())

    try:
        date_value = datetime(year, month, day)
    except ValueError:
        return ""

    if not (_DATE_RE.search(text) or _CN_DATE_RE.search(text)):
        current_day = _today_local().replace(tzinfo=None)
        if date_value > current_day + timedelta(days=1):
            try:
                date_value = date_value.replace(year=date_value.year - 1)
            except ValueError:
                return ""

    return date_value.strftime("%Y-%m-%d")


def _date_to_timestamp_ms(date_str: str) -> int:
    if not date_str:
        return 0
    tz = pytz.timezone(_TZ)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(tz.localize(dt).timestamp() * 1000)


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip(" \t\r\n·")
    title = re.sub(r"\s*\[(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\]\s*$", "", title)
    title = re.sub(r"\s+(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\s*$", "", title)
    return title.strip(" \t\r\n·")


def _is_valid_title(title: str, href: str) -> bool:
    normalized = title.strip().lower()
    if not title or len(title) < 6:
        return False
    if normalized in _SKIP_TITLES:
        return False
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return False
    return True


def _fetch_text(page_url: str, source_id: str) -> str:
    options = _SOURCE_PAGES[source_id]
    verify = options.get("verify", True)
    ignored = set(options.get("ignore_statuses", set()))

    if verify is False:
        response = requests.get(page_url, headers=DEFAULT_HEADERS, timeout=18, verify=False)
    else:
        response = fetch_raw(page_url, timeout=18)

    if response.status_code in ignored:
        logger.warning("%s returned ignored status %s", source_id, response.status_code)
        return ""

    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"
    text = response.text
    if "知道创宇云防御" in text or "连接超时" in text:
        logger.warning("%s returned an upstream protection page", source_id)
        return ""
    return text


def _html_fragments(text: str) -> List[str]:
    fragments = [text]
    fragments.extend(_CDATA_RE.findall(text))
    return fragments


def _anchor_context(anchor) -> str:
    for parent in anchor.parents:
        if getattr(parent, "name", None) not in {"li", "tr", "dd", "dt", "p", "div"}:
            continue
        if not hasattr(parent, "get_text"):
            continue
        text = parent.get_text(" ", strip=True)
        if len(text) > 600:
            continue
        if _DATE_RE.search(text) or _CN_DATE_RE.search(text) or _MONTH_DAY_RE.search(text):
            return text
    return anchor.get_text(" ", strip=True)


def _make_item(title: str, url: str, date_str: str) -> Dict[str, Any]:
    timestamp_ms = _date_to_timestamp_ms(date_str)
    return {
        "id": url,
        "title": title,
        "url": url,
        "pubDate": timestamp_ms,
        "extra": {
            "date": timestamp_ms,
            "info": date_str,
        },
    }


def _should_include(
    item: Dict[str, Any],
    context: Optional[SourceCrawlContext],
    seen_keys: set,
) -> bool:
    key = item.get("url") or item.get("title")
    if key in seen_keys:
        return False
    seen_keys.add(key)

    if context:
        if context.local_date_from_timestamp_ms(item.get("pubDate")) != context.crawl_date:
            return False
        if context.has_seen_item(item):
            return False
    return True


def _parse_anchor_items(
    source_id: str,
    page_url: str,
    html: str,
    context: Optional[SourceCrawlContext],
) -> List[Dict[str, Any]]:
    news: List[Dict[str, Any]] = []
    seen_keys = set()
    fallback_year = _fallback_year(context)

    for fragment in _html_fragments(html):
        soup = BeautifulSoup(fragment, HTML_PARSER)
        for anchor in soup.select("a[href]"):
            title = _clean_title(anchor.get("title") or anchor.get_text(" ", strip=True))
            href = str(anchor.get("href", "")).strip()
            if not _is_valid_title(title, href):
                continue

            context_text = _anchor_context(anchor)
            date_str = _normalize_date(context_text, fallback_year=fallback_year)
            if not date_str:
                continue

            item = _make_item(title, urljoin(page_url, href), date_str)
            if _should_include(item, context, seen_keys):
                news.append(item)

    news.sort(key=lambda item: item.get("pubDate", 0), reverse=True)
    return news if context else news[:50]


def _parse_camet_cards(
    page_url: str,
    html: str,
    context: Optional[SourceCrawlContext],
) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, HTML_PARSER)
    news: List[Dict[str, Any]] = []
    seen_keys = set()
    fallback_year = _fallback_year(context)

    for card in soup.select(".detail_box[data-link]"):
        title_node = card.select_one(".content-title")
        if not title_node:
            continue
        title = _clean_title(title_node.get_text(" ", strip=True))
        href = str(card.get("data-link", "")).strip()
        if not _is_valid_title(title, href):
            continue

        date_text = card.get_text(" ", strip=True)
        date_str = _normalize_date(date_text, fallback_year=fallback_year)
        if not date_str:
            continue

        item = _make_item(title, urljoin(page_url, href), date_str)
        if _should_include(item, context, seen_keys):
            news.append(item)

    news.sort(key=lambda item: item.get("pubDate", 0), reverse=True)
    return news if context else news[:50]


def _fetch_industry_source(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    page_url = _SOURCE_PAGES[source_id]["url"]
    html = _fetch_text(page_url, source_id)
    if not html:
        return []

    if _SOURCE_PAGES[source_id].get("mode") == "camet_cards":
        return _parse_camet_cards(page_url, html, context)
    return _parse_anchor_items(source_id, page_url, html, context)


def fetch_customs_stats(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("customs-stats", context)


def fetch_cpia_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("cpia-news", context)


def fetch_caam_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("caam-news", context)


def fetch_sac_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("sac-news", context)


def fetch_crea_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("crea-news", context)


def fetch_iachina_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("iachina-news", context)


def fetch_ceea_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("ceea-news", context)


def fetch_camet_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("camet-news", context)


def fetch_isc_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("isc-news", context)


def fetch_cpema_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_industry_source("cpema-news", context)


register_sources({
    "customs-stats": fetch_customs_stats,
    "cpia-news": fetch_cpia_news,
    "caam-news": fetch_caam_news,
    "sac-news": fetch_sac_news,
    "crea-news": fetch_crea_news,
    "iachina-news": fetch_iachina_news,
    "ceea-news": fetch_ceea_news,
    "camet-news": fetch_camet_news,
    "isc-news": fetch_isc_news,
    "cpema-news": fetch_cpema_news,
})
