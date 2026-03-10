# coding=utf-8
"""财联社 - API JSON + SHA-1/MD5 签名"""

from .base import register_sources, fetch
from .utils import cls_get_search_params


def _fetch_cls_depth():
    """深度"""
    url = "https://www.cls.cn/v3/depth/home/assembled/1000"
    params = cls_get_search_params()
    res = fetch(url, params=params, response_type="json")

    items = res.get("data", {}).get("depth_list", [])
    # 按 ctime 倒序
    items.sort(key=lambda x: x.get("ctime", 0), reverse=True)

    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title") or item.get("brief", ""),
            "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
            "mobileUrl": item.get("shareurl", ""),
            "pubDate": item.get("ctime", 0) * 1000,
        }
        for item in items
        if item.get("title") or item.get("brief")
    ]


def _fetch_cls_hot():
    """热门"""
    url = "https://www.cls.cn/v2/article/hot/list"
    params = cls_get_search_params()
    res = fetch(url, params=params, response_type="json")

    items = res.get("data", [])
    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("title") or item.get("brief", ""),
            "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
            "mobileUrl": item.get("shareurl", ""),
        }
        for item in items
        if item.get("title") or item.get("brief")
    ]


register_sources({
    "cls-depth": _fetch_cls_depth,
    "cls-hot": _fetch_cls_hot,
})
