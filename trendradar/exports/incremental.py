"""Build a portable package containing only records added by the current run."""

import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from trendradar.storage.base import NewsData, NewsItem, RSSData, RSSItem
from trendradar.utils.url import normalize_url


NewsIdentity = Tuple[str, str, str]
RSSIdentity = Tuple[str, str, str]


def _news_identity(item: NewsItem) -> NewsIdentity:
    if item.url:
        return (item.source_id, "url", normalize_url(item.url, item.source_id))
    return (item.source_id, "title", item.title.strip())


def _rss_identity(item: RSSItem) -> RSSIdentity:
    if item.url:
        return (item.feed_id, "url", item.url.strip())
    return (item.feed_id, "title", item.title.strip())


def _iter_news(data: Optional[NewsData]) -> Iterable[NewsItem]:
    if data is None:
        return
    for news_list in data.items.values():
        yield from news_list


def _iter_rss(data: Optional[RSSData]) -> Iterable[RSSItem]:
    if data is None:
        return
    for rss_list in data.items.values():
        yield from rss_list


def _new_news_items(
    before: Optional[NewsData],
    after: Optional[NewsData],
) -> List[NewsItem]:
    existing: Set[NewsIdentity] = {_news_identity(item) for item in _iter_news(before)}
    added: Dict[NewsIdentity, NewsItem] = {}
    for item in _iter_news(after):
        identity = _news_identity(item)
        if identity not in existing:
            added[identity] = item
    return sorted(
        added.values(),
        key=lambda item: (item.source_id, item.first_time or item.crawl_time, item.title),
    )


def _new_rss_items(
    before: Optional[RSSData],
    after: Optional[RSSData],
) -> List[RSSItem]:
    existing: Set[RSSIdentity] = {_rss_identity(item) for item in _iter_rss(before)}
    added: Dict[RSSIdentity, RSSItem] = {}
    for item in _iter_rss(after):
        identity = _rss_identity(item)
        if identity not in existing:
            added[identity] = item
    return sorted(
        added.values(),
        key=lambda item: (item.feed_id, item.published_at or item.first_time, item.title),
    )


def _serialize_news(item: NewsItem) -> Dict[str, Any]:
    return {
        "source_id": item.source_id,
        "source_name": item.source_name,
        "title": item.title,
        "rank": item.rank,
        "url": item.url,
        "mobile_url": item.mobile_url,
        "first_crawl_time": item.first_time or item.crawl_time,
        "last_crawl_time": item.last_time or item.crawl_time,
        "crawl_count": item.count,
    }


def _serialize_rss(item: RSSItem) -> Dict[str, Any]:
    return {
        "feed_id": item.feed_id,
        "feed_name": item.feed_name,
        "title": item.title,
        "url": item.url,
        "published_at": item.published_at,
        "summary": item.summary,
        "author": item.author,
        "first_crawl_time": item.first_time or item.crawl_time,
        "last_crawl_time": item.last_time or item.crawl_time,
        "crawl_count": item.count,
    }


def build_incremental_payload(
    *,
    before_news: Optional[NewsData],
    after_news: Optional[NewsData],
    before_rss: Optional[RSSData],
    after_rss: Optional[RSSData],
    generated_at: str,
    batch_metadata: Optional[Dict[str, str]] = None,
    failed_news_ids: Optional[List[str]] = None,
    failed_rss_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return records present after the crawl but absent from its baseline."""
    news_items = _new_news_items(before_news, after_news)
    rss_items = _new_rss_items(before_rss, after_rss)
    crawl_date = ""
    for data in (after_news, after_rss, before_news, before_rss):
        if data is not None and data.date:
            crawl_date = data.date
            break

    batch = {
        "generated_at": generated_at,
        "crawl_date": crawl_date,
    }
    if batch_metadata:
        batch.update({key: value for key, value in batch_metadata.items() if value})

    return {
        "schema_version": 1,
        "batch": batch,
        "counts": {
            "news": len(news_items),
            "rss": len(rss_items),
            "total": len(news_items) + len(rss_items),
        },
        "failed_sources": {
            "news": sorted(set(failed_news_ids or [])),
            "rss": sorted(set(failed_rss_ids or [])),
        },
        "news_items": [_serialize_news(item) for item in news_items],
        "rss_items": [_serialize_rss(item) for item in rss_items],
    }


def write_incremental_package(path: Path, payload: Dict[str, Any]) -> Path:
    """Atomically write a UTF-8 JSON payload compressed with gzip."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f"{target.name}.tmp")

    try:
        with gzip.open(temp_path, "wt", encoding="utf-8") as package_file:
            json.dump(payload, package_file, ensure_ascii=False, separators=(",", ":"))
            package_file.write("\n")
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return target
