# coding=utf-8
"""
爬虫模块 - 数据抓取功能

支持两种模式：
- direct: 内置爬虫直接抓取（默认）
- api: 通过 NewsNow API 间接获取（向后兼容）
"""

from trendradar.crawler.fetcher import DataFetcher
from trendradar.crawler.sources import SourceRegistry

__all__ = ["DataFetcher", "SourceRegistry"]
