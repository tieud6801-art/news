# coding=utf-8
"""抖音热榜 - API JSON（需动态 Cookie）"""

from .base import source_fetcher, fetch, fetch_raw


@source_fetcher("douyin")
def fetch_douyin():
    # 先获取 Cookie
    resp = fetch_raw("https://login.douyin.com/")
    cookies = resp.cookies
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

    url = (
        "https://www.douyin.com/aweme/v1/web/hot/search/list/"
        "?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1"
    )
    res = fetch(
        url,
        headers={"cookie": cookie_str},
        response_type="json",
    )
    items = res.get("data", {}).get("word_list", [])
    return [
        {
            "id": item["sentence_id"],
            "title": item["word"],
            "url": f"https://www.douyin.com/hot/{item['sentence_id']}",
        }
        for item in items
        if item.get("word")
    ]
