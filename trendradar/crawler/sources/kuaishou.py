# coding=utf-8
"""快手热榜 - HTML 内嵌 Apollo GraphQL State"""

import json
import re
from urllib.parse import quote

from .base import source_fetcher, fetch


@source_fetcher("kuaishou")
def fetch_kuaishou():
    html = fetch("https://www.kuaishou.com/?isHome=1", response_type="text")

    # 提取 window.__APOLLO_STATE__ 中的数据
    match = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.+?\});", html)
    if not match:
        raise ValueError("无法获取快手热榜数据")

    data = json.loads(match.group(1))
    client = data.get("defaultClient", {})
    root_query = client.get("ROOT_QUERY", {})

    # 获取热榜数据 ID
    hot_rank_key = 'visionHotRank({"page":"home"})'
    hot_rank_ref = root_query.get(hot_rank_key, {})
    hot_rank_id = hot_rank_ref.get("id", "")

    if not hot_rank_id:
        raise ValueError("无法获取快手热榜数据 ID")

    # 获取热榜列表数据
    hot_rank_data = client.get(hot_rank_id, {})
    items = hot_rank_data.get("items", [])

    news = []
    for item in items:
        item_id = item.get("id", "")
        item_data = client.get(item_id, {})

        # 过滤置顶
        if item_data.get("tagType") == "置顶":
            continue

        name = item_data.get("name", "")
        if not name:
            continue

        news.append({
            "id": item_id.replace("VisionHotRankItem:", ""),
            "title": name,
            "url": f"https://www.kuaishou.com/search/video?searchKey={quote(name)}",
            "extra": {
                "icon": item_data.get("iconUrl"),
            },
        })

    return news
