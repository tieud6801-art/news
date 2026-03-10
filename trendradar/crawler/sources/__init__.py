# coding=utf-8
"""
直接爬虫源模块

自动发现并注册所有数据源爬虫，替代 NewsNow API 调用。
"""

from .base import SourceRegistry, source_fetcher

# 导入所有源模块以触发注册
from . import (
    sspai,
    juejin,
    tencent,
    kaopu,
    mktnews,
    ithome,
    gelonghui,
    xinhua,
    cankaoxiaoxi,
    eastmoney,
    wallstreetcn,
    xueqiu,
    zaobao,
    sputniknewscn,
    kuaishou,
    cls,
    weibo,
    zhihu,
    baidu,
    toutiao,
    bilibili,
    thepaper,
    ifeng,
    tieba,
    douyin,
)

__all__ = ["SourceRegistry", "source_fetcher"]
