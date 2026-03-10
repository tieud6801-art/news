# coding=utf-8
"""
爬虫工具函数

移植自 NewsNow 的 server/utils/ 模块，提供：
- parse_relative_date: 中英文相对时间解析
- parse_jsonp: JSONP 格式响应解析
- md5 / sha1: 哈希工具（用于财联社签名）
- cls_sign: 财联社 API 签名计算
"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import pytz


# ============================================================
# 相对时间解析
# ============================================================

# 中文数字映射
_CN_NUMS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "两": 2, "半": 0.5}

# 中英文时间单位到 timedelta 参数名的映射
_UNIT_MAP = {
    "秒": "seconds", "second": "seconds", "seconds": "seconds", "sec": "seconds", "s": "seconds",
    "分": "minutes", "分钟": "minutes", "minute": "minutes", "minutes": "minutes", "min": "minutes",
    "时": "hours", "小时": "hours", "hour": "hours", "hours": "hours", "hr": "hours", "h": "hours",
    "天": "days", "日": "days", "day": "days", "days": "days", "d": "days",
    "周": "weeks", "星期": "weeks", "week": "weeks", "weeks": "weeks", "w": "weeks",
    "月": "months", "month": "months", "months": "months",
    "年": "years", "year": "years", "years": "years",
}

# 星期映射
_WEEKDAY_MAP = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6, "周天": 6,
    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6, "星期天": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def _parse_cn_number(s: str) -> float:
    """解析中文数字"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        pass
    if s in _CN_NUMS:
        return _CN_NUMS[s]
    # 处理如 "十一" = 11, "二十三" = 23
    if "十" in s:
        parts = s.split("十")
        tens = _CN_NUMS.get(parts[0], 1) if parts[0] else 1
        ones = _CN_NUMS.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return int(tens) * 10 + int(ones)
    return 0


def parse_relative_date(date_str: str, timezone: str = "Asia/Shanghai") -> datetime:
    """
    解析相对时间字符串为 datetime

    支持格式：
    - "刚刚" / "just now"
    - "3分钟前" / "3 minutes ago"
    - "今天 14:00" / "昨天 20:30"
    - "2024-01-01 14:00"
    - "周一 09:00"

    Args:
        date_str: 时间字符串
        timezone: 时区名称

    Returns:
        datetime 对象（带时区信息）
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    date_str = date_str.strip()

    if not date_str:
        return now

    # "刚刚" / "just now"
    if date_str in ("刚刚", "just now", "刚才", "just"):
        return now

    # 尝试解析标准日期格式
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%m-%d %H:%M",
        "%m/%d %H:%M",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:  # 没有年份
                dt = dt.replace(year=now.year)
            return tz.localize(dt)
        except ValueError:
            continue

    # "X前" / "X ago" 模式
    ago_match = re.match(
        r"(\d+\.?\d*)\s*(秒|分钟?|小时|时|天|日|周|星期|月|年|seconds?|minutes?|hours?|days?|weeks?|months?|years?|sec|min|hr|[smhdw])\s*(?:前|ago)?",
        date_str, re.IGNORECASE,
    )
    if ago_match:
        amount = float(ago_match.group(1))
        unit_str = ago_match.group(2).lower().rstrip("s") if ago_match.group(2) not in _UNIT_MAP else ago_match.group(2)
        unit = _UNIT_MAP.get(ago_match.group(2)) or _UNIT_MAP.get(unit_str, "minutes")

        if unit == "months":
            return now - timedelta(days=amount * 30)
        elif unit == "years":
            return now - timedelta(days=amount * 365)
        else:
            return now - timedelta(**{unit: amount})

    # "今天/昨天/前天 HH:MM" 模式
    day_time_match = re.match(
        r"(今天|今日|昨天|昨日|前天|前日|today|yesterday)\s*(\d{1,2}:\d{2}(?::\d{2})?)?",
        date_str, re.IGNORECASE,
    )
    if day_time_match:
        day_word = day_time_match.group(1).lower()
        time_str = day_time_match.group(2)

        day_offsets = {
            "今天": 0, "今日": 0, "today": 0,
            "昨天": -1, "昨日": -1, "yesterday": -1,
            "前天": -2, "前日": -2,
        }
        offset = day_offsets.get(day_word, 0)
        target = now + timedelta(days=offset)

        if time_str:
            parts = time_str.split(":")
            target = target.replace(hour=int(parts[0]), minute=int(parts[1]),
                                    second=int(parts[2]) if len(parts) > 2 else 0, microsecond=0)
        return target

    # 星期模式 "周一 09:00"
    for key, weekday in _WEEKDAY_MAP.items():
        if date_str.lower().startswith(key):
            time_part = date_str[len(key):].strip()
            days_diff = (now.weekday() - weekday) % 7
            if days_diff == 0 and time_part:
                # 当天
                pass
            target = now - timedelta(days=days_diff)
            if time_part:
                time_match = re.match(r"(\d{1,2}):(\d{2})", time_part)
                if time_match:
                    target = target.replace(
                        hour=int(time_match.group(1)),
                        minute=int(time_match.group(2)),
                        second=0, microsecond=0,
                    )
            return target

    # 最后尝试 dateutil 宽松解析
    try:
        from dateutil import parser as dateutil_parser
        dt = dateutil_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        return dt
    except Exception:
        pass

    # 无法解析，返回当前时间
    return now


def transform_to_utc(date_str: str, fmt: Optional[str] = None, timezone: str = "Asia/Shanghai") -> int:
    """
    将指定时区的时间字符串转为 UTC 毫秒时间戳

    Args:
        date_str: 时间字符串
        fmt: 可选的 strptime 格式
        timezone: 源时区

    Returns:
        UTC 毫秒时间戳
    """
    tz = pytz.timezone(timezone)
    if fmt:
        dt = datetime.strptime(date_str, fmt)
    else:
        dt = parse_relative_date(date_str, timezone)
        if dt.tzinfo:
            return int(dt.timestamp() * 1000)

    dt = tz.localize(dt)
    return int(dt.timestamp() * 1000)


# ============================================================
# JSONP / JS 变量解析
# ============================================================

def parse_jsonp(text: str, var_name: str = "ajaxResult") -> Any:
    """
    解析 JSONP 或 JS 变量赋值格式的响应

    支持格式:
    - var ajaxResult={...}
    - var newest=[...]
    - callback({...})

    Args:
        text: 原始响应文本
        var_name: 变量名

    Returns:
        解析后的 Python 对象
    """
    # 尝试 var name = {...}; 格式
    pattern = rf"var\s+{re.escape(var_name)}\s*=\s*"
    match = re.search(pattern, text)
    if match:
        json_str = text[match.end():].rstrip().rstrip(";").strip()
        return json.loads(json_str)

    # 尝试 callback({...}) 格式
    callback_match = re.match(r"\w+\s*\((.+)\)\s*;?\s*$", text, re.DOTALL)
    if callback_match:
        return json.loads(callback_match.group(1))

    # 直接尝试 JSON 解析
    return json.loads(text)


# ============================================================
# 哈希 / 签名工具
# ============================================================

def md5(s: str) -> str:
    """计算 MD5 哈希"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def sha1(s: str) -> str:
    """计算 SHA-1 哈希"""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def cls_get_search_params(extra_params: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    生成财联社 API 签名参数

    移植自 NewsNow cls/utils.ts（参考 RSSHub 实现）

    Returns:
        带签名的查询参数字典
    """
    base_params = {
        "appName": "CailianpressWeb",
        "os": "web",
        "sv": "7.7.5",
    }
    if extra_params:
        base_params.update(extra_params)

    # 按 key 排序
    sorted_params = sorted(base_params.items())
    query_string = urlencode(sorted_params)

    # SHA-1 → MD5
    sha1_hash = sha1(query_string)
    sign = md5(sha1_hash)

    base_params["sign"] = sign
    return base_params
