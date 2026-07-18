# coding=utf-8
"""中国政府/部委权威政策源。"""

import ast
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import pytz
from bs4 import BeautifulSoup

from .base import HTML_PARSER, SourceCrawlContext, fetch, fetch_raw, get_session, register_sources


_TZ = "Asia/Shanghai"
_DATE_RE = re.compile(r"((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})")
_CN_DATE_RE = re.compile(r"((?:19|20)\d{2})年(\d{1,2})月(\d{1,2})")
_COMPACT_DATE_RE = re.compile(r"((?:19|20)\d{2})(\d{2})(\d{2})")
_MONTH_DAY_RE = re.compile(r"(?<!\d)(\d{1,2})[-/](\d{1,2})(?!\d)")

_GOV_POLICY_JSON = {
    "gov-zhengce-zuixin": "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json",
    "gov-zhengce-jiedu": "https://www.gov.cn/zhengce/jiedu/ZCJD_QZ.json",
    "gov-zhengceku-bmwj": "https://www.gov.cn/zhengce/zhengceku/bmwj/TONGYONGGAILAN.json",
    "gov-zhengceku-gwywj": "https://www.gov.cn/zhengce/zhengceku/gwywj/TONGYONGGAILAN.json",
}

_STATIC_LIST_PAGES = {
    "cac-zcfg": "https://www.cac.gov.cn/wxzw/zcfg/A093703index_1.htm",
    "cac-data-zcfg": "https://www.cac.gov.cn/wxzw/sjzl/zcfg/A09370805index_1.htm",
    "nda-xwfb": "https://www.nda.gov.cn/sjj/swdt/xwfb/list/index_pc_1.html",
    "nda-tzgg": "https://www.nda.gov.cn/sjj/zwgk/tzgg/list/index_pc_1.html",
    "ndrc-tzgg": "https://www.ndrc.gov.cn/xwdt/tzgg/",
    "ndrc-xwfb": "https://www.ndrc.gov.cn/xwdt/xwfb/",
    "mof-zcfb": "https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/",
    "moa-flfg": "https://fgs.moa.gov.cn/flfg/",
    "moa-zfjd": "https://fgs.moa.gov.cn/zfjd/",
    "pbc-news": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
    "safe-whxw": "https://www.safe.gov.cn/safe/whxw/index.html",
    "safe-zcfg": "https://www.safe.gov.cn/safe/zcfg/index.html",
    "safe-zcfgjd": "https://www.safe.gov.cn/safe/zcfgjd/index.html",
}

_NHSA_RECORD_PAGES = {
    "nhsa-zcfg": "https://www.nhsa.gov.cn/col/col104/index.html",
    "nhsa-zcjd": "https://www.nhsa.gov.cn/col/col105/index.html",
}

_AUTHORIZED_READ_PAGES = {
    "mofcom-zcfb": "https://www.mofcom.gov.cn/zwgk/zcfb/",
    "miit-zcjd": "https://www.miit.gov.cn/zwgk/zcjd/index.html",
}

_MOE_HOME_SECTIONS = {
    "moe-newest-file": "nine_con1",
    "moe-policy-anal": "tt_con2",
}

_CHINATAX_LATEST_API = "https://www.chinatax.gov.cn/getFileListByCodeId"
_CSRC_NEWS_API = "https://www.csrc.gov.cn/searchList/a1a078ee0bc54721ab6b148884c784a8"
_NFRA_DOC_API = "https://www.nfra.gov.cn/cbircweb/DocInfo/SelectDocByItemIdAndChild"
_NFRA_DETAIL_URL = "https://www.nfra.gov.cn/cn/view/pages/ItemDetail.html"
_NFRA_ITEMS = {
    "nfra-gfxwj": 928,
    "nfra-jgdt": 915,
}
NFRA_ITEM_LIST_URLS = {
    "nfra-gfxwj": (
        "https://www.nfra.gov.cn/cn/view/pages/ItemList.html"
        "?itemPId=926&itemId=928&itemUrl=ItemListRightList.html"
        "&itemName=%E6%94%BF%E7%AD%96%E8%A7%84%E7%AB%A0%E8%A7%84%E8%8C%83%E6%80%A7%E6%96%87%E4%BB%B6"
    ),
    "nfra-jgdt": (
        "https://www.nfra.gov.cn/cn/view/pages/ItemList.html"
        "?itemPId=914&itemId=915&itemUrl=ItemListRightList.html"
        "&itemName=%E7%9B%91%E7%AE%A1%E5%8A%A8%E6%80%81"
    ),
}


def _default_year() -> int:
    return datetime.now(pytz.timezone(_TZ)).year


def _date_to_timestamp_ms(date_str: str, fallback_year: Optional[int] = None) -> int:
    date_str = _normalize_date(date_str, fallback_year=fallback_year)
    if not date_str:
        return 0
    tz = pytz.timezone(_TZ)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(tz.localize(dt).timestamp() * 1000)


def _normalize_date(text: str, fallback_year: Optional[int] = None) -> str:
    fallback_year = fallback_year or _default_year()
    match = _DATE_RE.search(text or "")
    if not match:
        match = _CN_DATE_RE.search(text or "")
    if not match:
        match = _COMPACT_DATE_RE.search(text or "")
    if not match:
        month_day_match = _MONTH_DAY_RE.search(text or "")
        if not month_day_match:
            return ""
        month, day = month_day_match.groups()
        year = fallback_year
    else:
        year, month, day = match.groups()

    year = int(year)
    month = int(month)
    day = int(day)
    try:
        datetime(year, month, day)
    except ValueError:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _should_include(
    news_item: Dict[str, Any],
    timestamp_ms: int,
    context: Optional[SourceCrawlContext],
    seen_keys: set,
) -> bool:
    key = news_item.get("url") or news_item.get("id") or news_item.get("title")
    if key in seen_keys:
        return False
    seen_keys.add(key)

    if context:
        if not context.is_crawl_date_timestamp_ms(timestamp_ms):
            return False
        if context.has_seen_item(news_item):
            return False

    return True


def _build_item(title: str, url: str, date_str: str, fallback_year: Optional[int] = None) -> Dict[str, Any]:
    timestamp_ms = _date_to_timestamp_ms(date_str, fallback_year=fallback_year)
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


def _fetch_gov_policy_json(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    data = fetch(_GOV_POLICY_JSON[source_id], response_type="json", timeout=20)
    news: List[Dict[str, Any]] = []
    seen_keys = set()

    for row in data:
        title = str(row.get("TITLE", "")).strip()
        url = str(row.get("URL", "")).strip()
        date_str = _normalize_date(str(row.get("DOCRELPUBTIME", "")))
        if not title or not url or not date_str:
            continue

        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, url, date_str)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)

    news.sort(key=lambda item: item.get("pubDate", 0), reverse=True)
    return news if context else news[:50]


def _find_date_for_anchor(anchor, fallback_year: Optional[int] = None) -> str:
    title = (anchor.get("title") or anchor.get_text(" ", strip=True)).strip()
    href = str(anchor.get("href", "")).strip()
    parent = anchor.find_parent(["li", "tr", "div", "p"])
    parent_text = parent.get_text(" ", strip=True) if parent else ""
    return _normalize_date(" ".join([parent_text, title, href]), fallback_year=fallback_year)


def _fetch_static_list(page_url: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    response = fetch_raw(page_url, timeout=15)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, HTML_PARSER)
    news: List[Dict[str, Any]] = []
    seen_keys = set()
    fallback_year = int(context.crawl_date[:4]) if context else _default_year()

    for a in soup.select("a[href]"):
        title = (a.get("title") or a.get_text(" ", strip=True)).strip()
        href = str(a.get("href", "")).strip()
        if not title or len(title) < 6 or not href:
            continue

        date_str = _find_date_for_anchor(a, fallback_year=fallback_year)
        if not date_str:
            continue
        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, urljoin(page_url, href), date_str, fallback_year=fallback_year)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def _fetch_nhsa_records(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    page_url = _NHSA_RECORD_PAGES[source_id]
    response = fetch_raw(page_url, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"

    record_html_list = re.findall(r"<record><!\[CDATA\[(.*?)\]\]></record>", response.text, flags=re.S)
    news: List[Dict[str, Any]] = []
    seen_keys = set()
    fallback_year = int(context.crawl_date[:4]) if context else _default_year()

    for record_html in record_html_list:
        soup = BeautifulSoup(record_html, HTML_PARSER)
        a = soup.select_one("a[href]")
        if not a:
            continue

        title = (a.get("title") or a.get_text(" ", strip=True)).strip()
        href = str(a.get("href", "")).strip()
        span_text = " ".join(span.get_text(" ", strip=True) for span in reversed(soup.select("span")))
        date_str = _normalize_date(span_text, fallback_year=fallback_year)
        if not date_str:
            date_str = _normalize_date(soup.get_text(" ", strip=True), fallback_year=fallback_year)
        if not title or not href or not date_str:
            continue
        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, urljoin(page_url, href), date_str, fallback_year=fallback_year)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def _fetch_moe_home_section(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    page_url = "http://www.moe.gov.cn/"
    response = fetch_raw(page_url, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"

    soup = BeautifulSoup(response.text, HTML_PARSER)
    section = soup.select_one(f"div#{_MOE_HOME_SECTIONS[source_id]}")
    if not section:
        return []

    news: List[Dict[str, Any]] = []
    seen_keys = set()
    fallback_year = int(context.crawl_date[:4]) if context else _default_year()
    for li in section.select("li"):
        a = li.select_one("a[href]")
        if not a:
            continue
        title = (a.get("title") or a.get_text(" ", strip=True)).strip()
        href = str(a.get("href", "")).strip()
        if not title or not href:
            continue

        date_str = _normalize_date(li.get_text(" ", strip=True) + " " + href, fallback_year=fallback_year)
        if not date_str:
            continue
        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, urljoin(page_url, href), date_str, fallback_year=fallback_year)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def _fetch_authorized_read_html(page_url: str) -> str:
    response = fetch_raw(page_url, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding or "utf-8"

    soup = BeautifulSoup(response.text, HTML_PARSER)
    script = soup.select_one("script[url][queryData]")
    if not script:
        return ""

    query_data = script.get("querydata") or script.get("queryData") or ""
    api_url = urljoin(page_url, str(script.get("url", "")))
    params = ast.literal_eval(query_data)
    result = fetch(
        api_url,
        headers={"Referer": page_url},
        params=params,
        response_type="json",
        timeout=15,
    )
    return result.get("data", {}).get("html", "")


def _fetch_authorized_read_list(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    page_url = _AUTHORIZED_READ_PAGES[source_id]
    html = _fetch_authorized_read_html(page_url)
    if not html:
        return []

    soup = BeautifulSoup(html, HTML_PARSER)
    news: List[Dict[str, Any]] = []
    seen_keys = set()

    for li in soup.select("li"):
        a = li.select_one("a[href]")
        if not a:
            continue
        title = (a.get("title") or a.get_text(" ", strip=True)).strip()
        date_str = _normalize_date(li.get_text(" ", strip=True))
        if not title or not date_str:
            continue

        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, urljoin(page_url, str(a.get("href", ""))), date_str)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def fetch_chinatax_latest(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    session = get_session()
    response = session.post(
        _CHINATAX_LATEST_API,
        data={
            "codeId": "",
            "channelId": "29a88b67e4b149cfa9fac7919dfb08a5",
            "page": 1,
            "size": 20,
        },
        headers={"Referer": "https://fgk.chinatax.gov.cn/"},
        timeout=15,
    )
    response.raise_for_status()
    rows = response.json().get("results", {}).get("data", {}).get("results", [])

    news: List[Dict[str, Any]] = []
    seen_keys = set()
    for row in rows:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        date_str = _normalize_date(str(row.get("publishedTimeStr", "")))
        if not title or not url or not date_str:
            continue

        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, url, date_str)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def fetch_csrc_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    result = fetch(
        _CSRC_NEWS_API,
        headers={"Referer": "https://www.csrc.gov.cn/csrc/c100028/common_xq_list.shtml"},
        params={
            "_isAgg": "true",
            "_isJson": "true",
            "_pageSize": 20,
            "_template": "index",
            "_rangeTimeGte": "",
            "_channelName": "",
            "page": 1,
        },
        response_type="json",
        timeout=15,
    )
    rows = result.get("data", {}).get("results", [])

    news: List[Dict[str, Any]] = []
    seen_keys = set()
    for row in rows:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        date_str = _normalize_date(str(row.get("publishedTimeStr", "")))
        if not title or not url or not date_str:
            continue
        if url.startswith("//"):
            url = f"https:{url}"

        if context and date_str != context.crawl_date:
            continue

        item = _build_item(title, url, date_str)
        if _should_include(item, item["pubDate"], context, seen_keys):
            news.append(item)
        if not context and len(news) >= 50:
            break

    return news


def _fetch_nfra_item(source_id: str, context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    item_id = _NFRA_ITEMS[source_id]
    page_size = 20
    max_pages = context.max_pages if context else 1
    news: List[Dict[str, Any]] = []
    seen_keys = set()
    for page_index in range(1, max_pages + 1):
        result = fetch(
            _NFRA_DOC_API,
            headers={"Referer": NFRA_ITEM_LIST_URLS[source_id]},
            params={
                "itemId": item_id,
                "pageIndex": page_index,
                "pageSize": page_size,
            },
            response_type="json",
            timeout=15,
        )
        rows = result.get("data", {}).get("rows", [])
        reached_older_item = False

        for row in rows:
            title = str(row.get("docSubtitle") or row.get("docTitle") or "").strip()
            date_str = _normalize_date(str(row.get("publishDate") or row.get("builddate") or ""))
            doc_id = str(row.get("docId") or "").strip()
            if not title or not date_str or not doc_id:
                continue
            if context and date_str < context.crawl_date:
                reached_older_item = True
                continue
            if context and date_str != context.crawl_date:
                continue

            if str(row.get("isTitleLink")) == "1" and row.get("titleLink"):
                url = urljoin("https://www.nfra.gov.cn/", str(row.get("titleLink")))
            else:
                generaltype = str(row.get("generaltype") or "0")
                url = f"{_NFRA_DETAIL_URL}?docId={doc_id}&itemId={item_id}&generaltype={generaltype}"

            item = _build_item(title, url, date_str)
            if _should_include(item, item["pubDate"], context, seen_keys):
                news.append(item)

        if not context or reached_older_item or len(rows) < page_size:
            break

    return news


def fetch_nfra_gfxwj(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_nfra_item("nfra-gfxwj", context)


def fetch_nfra_jgdt(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_nfra_item("nfra-jgdt", context)


def fetch_gov_zhengceku_bmwj(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_gov_policy_json("gov-zhengceku-bmwj", context)


def fetch_gov_zhengceku_gwywj(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_gov_policy_json("gov-zhengceku-gwywj", context)


def fetch_gov_zhengce_zuixin(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_gov_policy_json("gov-zhengce-zuixin", context)


def fetch_gov_zhengce_jiedu(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_gov_policy_json("gov-zhengce-jiedu", context)


def fetch_ndrc_tzgg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["ndrc-tzgg"], context)


def fetch_ndrc_xwfb(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["ndrc-xwfb"], context)


def fetch_cac_zcfg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["cac-zcfg"], context)


def fetch_cac_data_zcfg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["cac-data-zcfg"], context)


def fetch_nda_xwfb(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["nda-xwfb"], context)


def fetch_nda_tzgg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["nda-tzgg"], context)


def fetch_mofcom_zcfb(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_authorized_read_list("mofcom-zcfb", context)


def fetch_miit_zcjd(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_authorized_read_list("miit-zcjd", context)


def fetch_mof_zcfb(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["mof-zcfb"], context)


def fetch_moe_newest_file(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_moe_home_section("moe-newest-file", context)


def fetch_moe_policy_anal(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_moe_home_section("moe-policy-anal", context)


def fetch_moa_flfg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["moa-flfg"], context)


def fetch_moa_zfjd(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["moa-zfjd"], context)


def fetch_pbc_news(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["pbc-news"], context)


def fetch_safe_whxw(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["safe-whxw"], context)


def fetch_safe_zcfg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["safe-zcfg"], context)


def fetch_safe_zcfgjd(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_static_list(_STATIC_LIST_PAGES["safe-zcfgjd"], context)


def fetch_nhsa_zcfg(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_nhsa_records("nhsa-zcfg", context)


def fetch_nhsa_zcjd(context: Optional[SourceCrawlContext] = None) -> List[Dict[str, Any]]:
    return _fetch_nhsa_records("nhsa-zcjd", context)


register_sources({
    "gov-zhengce-zuixin": fetch_gov_zhengce_zuixin,
    "gov-zhengce-jiedu": fetch_gov_zhengce_jiedu,
    "gov-zhengceku-bmwj": fetch_gov_zhengceku_bmwj,
    "gov-zhengceku-gwywj": fetch_gov_zhengceku_gwywj,
    "ndrc-tzgg": fetch_ndrc_tzgg,
    "ndrc-xwfb": fetch_ndrc_xwfb,
    "cac-zcfg": fetch_cac_zcfg,
    "cac-data-zcfg": fetch_cac_data_zcfg,
    "nda-xwfb": fetch_nda_xwfb,
    "nda-tzgg": fetch_nda_tzgg,
    "mofcom-zcfb": fetch_mofcom_zcfb,
    "miit-zcjd": fetch_miit_zcjd,
    "mof-zcfb": fetch_mof_zcfb,
    "moe-newest-file": fetch_moe_newest_file,
    "moe-policy-anal": fetch_moe_policy_anal,
    "moa-flfg": fetch_moa_flfg,
    "moa-zfjd": fetch_moa_zfjd,
    "chinatax-latest": fetch_chinatax_latest,
    "pbc-news": fetch_pbc_news,
    "safe-whxw": fetch_safe_whxw,
    "safe-zcfg": fetch_safe_zcfg,
    "safe-zcfgjd": fetch_safe_zcfgjd,
    "csrc-news": fetch_csrc_news,
    "nfra-gfxwj": fetch_nfra_gfxwj,
    "nfra-jgdt": fetch_nfra_jgdt,
    "nhsa-zcfg": fetch_nhsa_zcfg,
    "nhsa-zcjd": fetch_nhsa_zcjd,
})
