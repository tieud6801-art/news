# coding=utf-8
"""
数据获取器模块

支持两种数据获取模式：
- direct: 直接爬取（内置爬虫，无需依赖外部 API）
- api: 通过 NewsNow API 间接获取（向后兼容）

默认使用 direct 模式。
"""

import json
import logging
import random
import time
from typing import Dict, List, Tuple, Optional, Union

import requests

logger = logging.getLogger("trendradar.crawler.fetcher")


class DataFetcher:
    """数据获取器（支持直接爬取和 API 两种模式）"""

    # 默认 API 地址（仅 api 模式使用）
    DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        api_url: Optional[str] = None,
        default_fetch_mode: str = "direct",
    ):
        """
        初始化数据获取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            api_url: API 基础 URL（可选，默认使用 DEFAULT_API_URL）
            default_fetch_mode: 默认获取模式 - "direct"(直接爬取) 或 "api"(NewsNow API)
        """
        self.proxy_url = proxy_url
        self.api_url = api_url or self.DEFAULT_API_URL
        self.default_fetch_mode = default_fetch_mode

        # 延迟导入源注册表（避免循环导入）
        self._source_registry = None

    def _get_source_registry(self):
        """延迟加载源注册表"""
        if self._source_registry is None:
            from trendradar.crawler.sources import SourceRegistry
            self._source_registry = SourceRegistry
        return self._source_registry

    def fetch_data(
        self,
        id_info: Union[str, Tuple[str, str]],
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """
        获取指定ID数据，支持重试

        Args:
            id_info: 平台ID 或 (平台ID, 别名) 元组
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间（秒）
            max_retry_wait: 最大重试等待时间（秒）

        Returns:
            (响应文本, 平台ID, 别名) 元组，失败时响应文本为 None
        """
        if isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value

        url = f"{self.api_url}?id={id_value}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=10,
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "未知")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                print(f"获取 {id_value} 成功（{status_info}）")
                return data_text, id_value, alias

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"请求 {id_value} 失败: {e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求 {id_value} 失败: {e}")
                    return None, id_value, alias

        return None, id_value, alias

    def fetch_data_direct(
        self,
        id_info: Union[str, Tuple[str, str]],
        max_retries: int = 2,
    ) -> Tuple[Optional[List[Dict]], str, str]:
        """
        直接爬取数据（不通过 NewsNow API）

        Args:
            id_info: 平台ID 或 (平台ID, 别名) 元组
            max_retries: 最大重试次数

        Returns:
            (数据项列表, 平台ID, 别名) 元组，失败时数据列表为 None
        """
        if isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value

        registry = self._get_source_registry()

        if not registry.has(id_value):
            logger.warning(f"源 {id_value} 未注册直接爬虫，回退到 API 模式")
            # 回退到 API 模式
            response, _, _ = self.fetch_data(id_info, max_retries=max_retries)
            if response:
                data = json.loads(response)
                return data.get("items", []), id_value, alias
            return None, id_value, alias

        retries = 0
        while retries <= max_retries:
            try:
                items = registry.fetch(id_value)
                print(f"[直接爬取] 获取 {id_value} 成功（{len(items)} 条）")
                return items, id_value, alias
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    wait_time = random.uniform(2, 4) + (retries - 1)
                    logger.warning(f"[直接爬取] {id_value} 失败: {e}，{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[直接爬取] {id_value} 最终失败: {e}")
                    return None, id_value, alias

        return None, id_value, alias

    def _convert_items_to_results(self, id_value: str, items: List[Dict]) -> Dict:
        """
        将爬虫返回的 items 列表转换为 crawl_websites 的结果格式

        Args:
            id_value: 平台 ID
            items: 爬虫返回的数据列表

        Returns:
            {title: {"ranks": [rank], "url": ..., "mobileUrl": ...}} 字典
        """
        result = {}
        for index, item in enumerate(items, 1):
            title = item.get("title")
            if title is None or isinstance(title, float) or not str(title).strip():
                continue
            title = str(title).strip()
            url = item.get("url", "")
            mobile_url = item.get("mobileUrl", item.get("mobileUrl", ""))

            if title in result:
                result[title]["ranks"].append(index)
            else:
                result[title] = {
                    "ranks": [index],
                    "url": url,
                    "mobileUrl": mobile_url,
                }
        return result

    def crawl_websites(
        self,
        ids_list: List[Union[str, Tuple[str, str]]],
        request_interval: int = 100,
        fetch_mode: Optional[str] = None,
    ) -> Tuple[Dict, Dict, List]:
        """
        爬取多个网站数据

        Args:
            ids_list: 平台ID列表，每个元素可以是字符串或 (平台ID, 别名) 元组
            request_interval: 请求间隔（毫秒）
            fetch_mode: 获取模式覆盖 - "direct" / "api" / None(使用默认)

        Returns:
            (结果字典, ID到名称的映射, 失败ID列表) 元组
        """
        mode = fetch_mode or self.default_fetch_mode
        results = {}
        id_to_name = {}
        failed_ids = []

        for i, id_info in enumerate(ids_list):
            if isinstance(id_info, tuple):
                id_value, name = id_info
            else:
                id_value = id_info
                name = id_value

            id_to_name[id_value] = name

            if mode == "direct":
                # 直接爬取模式
                items, _, _ = self.fetch_data_direct(id_info)
                if items is not None:
                    results[id_value] = self._convert_items_to_results(id_value, items)
                else:
                    failed_ids.append(id_value)
            else:
                # API 模式（向后兼容）
                response, _, _ = self.fetch_data(id_info)
                if response:
                    try:
                        data = json.loads(response)
                        results[id_value] = self._convert_items_to_results(
                            id_value, data.get("items", [])
                        )
                    except json.JSONDecodeError:
                        print(f"解析 {id_value} 响应失败")
                        failed_ids.append(id_value)
                    except Exception as e:
                        print(f"处理 {id_value} 数据出错: {e}")
                        failed_ids.append(id_value)
                else:
                    failed_ids.append(id_value)

            # 请求间隔（除了最后一个）
            if i < len(ids_list) - 1:
                actual_interval = request_interval + random.randint(-10, 20)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        print(f"成功: {list(results.keys())}, 失败: {failed_ids}")
        return results, id_to_name, failed_ids
