"""
信号识别与事件分类

基于公告标题关键词匹配，识别事件类型并映射优先级。
支持 YAML 配置的关键词库和排除词规则。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import yaml

from .models import (
    Announcement, EVENT_TYPE_UNKNOWN, SIGNAL_NONE,
    EVENT_TYPE_M_A, EVENT_TYPE_CAP_EXPAND, EVENT_TYPE_BIZ_CHANGE,
    EVENT_TYPE_TECH_COOP, EVENT_TYPE_ORDER, EVENT_TYPE_OTHER,
    SIGNAL_P0, SIGNAL_P1, SIGNAL_P2,
    ANN_STATUS_SIGNAL_MATCHED, ANN_STATUS_NO_SIGNAL,
)

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS_PATH = "config/signal_keywords.yaml"


def _load_keywords(path: Optional[str] = None) -> dict:
    path = path or DEFAULT_KEYWORDS_PATH
    p = Path(path)
    if not p.exists():
        logger.warning("Keywords file not found: %s, using built-in defaults", p)
        return _default_keywords()
    try:
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("event_types", {}) if isinstance(data, dict) else _default_keywords()
    except Exception as e:
        logger.error("Failed to load keywords from %s: %s", path, e)
        return _default_keywords()


def _default_keywords() -> dict:
    return {
        EVENT_TYPE_M_A: {
            "priority": SIGNAL_P0,
            "include_keywords": ["收购", "并购", "重组", "借壳", "吸收合并"],
            "exclude_keywords": ["出售", "转让", "减持"],
            "min_title_length": 4,
        },
        EVENT_TYPE_CAP_EXPAND: {
            "priority": SIGNAL_P0,
            "include_keywords": ["投资建设", "扩产", "新建项目", "产能扩建", "生产基地", "投产"],
            "exclude_keywords": [],
            "min_title_length": 4,
        },
        EVENT_TYPE_BIZ_CHANGE: {
            "priority": SIGNAL_P1,
            "include_keywords": ["经营范围变更", "新增业务", "跨界", "转型", "进军", "布局", "战略转型"],
            "exclude_keywords": ["注销", "减少"],
            "min_title_length": 4,
        },
        EVENT_TYPE_TECH_COOP: {
            "priority": SIGNAL_P1,
            "include_keywords": ["战略合作", "签订协议", "联合研发", "技术许可", "合作协议", "技术合作"],
            "exclude_keywords": ["终止", "解除"],
            "min_title_length": 4,
        },
        EVENT_TYPE_ORDER: {
            "priority": SIGNAL_P2,
            "include_keywords": ["重大合同", "中标", "订单", "框架协议", "供货合同", "销售合同"],
            "exclude_keywords": ["解除", "取消"],
            "min_title_length": 4,
        },
    }


def identify(announcement: Announcement, keywords_config: Optional[dict] = None) -> Announcement:
    """
    对单条公告进行信号识别，返回更新后的 Announcement 对象。
    识别结果写入 event_type、signal_priority、status 字段。
    """
    if keywords_config is None:
        keywords_config = _load_keywords()

    title = announcement.title or ""
    if len(title) < 4:
        announcement.status = ANN_STATUS_NO_SIGNAL
        return announcement

    # Try each event type
    matched_type = None
    matched_priority = SIGNAL_NONE

    for event_type, config in keywords_config.items():
        include = config.get("include_keywords", [])
        exclude = config.get("exclude_keywords", [])
        min_len = config.get("min_title_length", 4)

        if len(title) < min_len:
            continue

        # Check exclude first
        if any(kw in title for kw in exclude):
            continue

        # Check include
        if any(kw in title for kw in include):
            matched_type = event_type
            matched_priority = config.get("priority", SIGNAL_NONE)
            break

    if matched_type:
        announcement.event_type = matched_type
        announcement.signal_priority = matched_priority
        announcement.status = ANN_STATUS_SIGNAL_MATCHED
    else:
        announcement.event_type = EVENT_TYPE_OTHER
        announcement.signal_priority = SIGNAL_NONE
        announcement.status = ANN_STATUS_NO_SIGNAL

    return announcement


def batch_identify(
    announcements: list[Announcement],
    keywords_config: Optional[dict] = None,
) -> list[Announcement]:
    """批量信号识别"""
    return [identify(a, keywords_config) for a in announcements]


def classify_event_type(title: str) -> str:
    """快速判断一条标题的事件类型（不修改对象）"""
    configs = _load_keywords()
    for event_type, config in configs.items():
        include = config.get("include_keywords", [])
        exclude = config.get("exclude_keywords", [])
        if any(kw in title for kw in exclude):
            continue
        if any(kw in title for kw in include):
            return event_type
    return EVENT_TYPE_UNKNOWN
