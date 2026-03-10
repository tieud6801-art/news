# coding=utf-8
"""参考消息 - API JSON（多频道并发）"""

from concurrent.futures import ThreadPoolExecutor

from .base import source_fetcher, fetch
from .utils import transform_to_utc

_CHANNELS = ["zhongguo", "guandian", "gj"]


def _fetch_channel(channel: str):
    """抓取单个频道"""
    url = f"https://china.cankaoxiaoxi.com/json/channel/{channel}/list.json"
    return fetch(url, response_type="json")


@source_fetcher("cankaoxiaoxi")
def fetch_cankaoxiaoxi():
    # 并发请求 3 个频道
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_fetch_channel, ch): ch for ch in _CHANNELS}
        results = []
        for future in futures:
            try:
                res = future.result(timeout=15)
                items = res.get("list", [])
                results.extend(items)
            except Exception:
                continue

    news = []
    for item in results:
        data = item.get("data", {})
        title = data.get("title", "")
        if not title:
            continue

        pub_time = data.get("publishTime", "")
        date_ts = transform_to_utc(pub_time) if pub_time else 0

        news.append({
            "id": data.get("id", ""),
            "title": title,
            "url": data.get("url", ""),
            "extra": {
                "date": date_ts,
            },
        })

    # 按时间倒序
    news.sort(key=lambda x: x.get("extra", {}).get("date", 0), reverse=True)
    return news
