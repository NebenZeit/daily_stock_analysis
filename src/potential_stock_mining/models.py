"""
潜力标的智能挖掘系统 — 数据实体定义

所有实体使用 Python dataclass，序列化为 JSON 存入文件。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ─── Event types ──────────────────────────────────────────────
EVENT_TYPE_M_A = "M_A"           # 并购重组
EVENT_TYPE_CAP_EXPAND = "CAP_EXPAND"  # 产能扩张
EVENT_TYPE_BIZ_CHANGE = "BIZ_CHANGE"  # 业务变更/跨界
EVENT_TYPE_TECH_COOP = "TECH_COOP"    # 技术合作
EVENT_TYPE_ORDER = "ORDER"            # 订单落地
EVENT_TYPE_OTHER = "OTHER"
EVENT_TYPE_UNKNOWN = "UNKNOWN"

# ─── Signal priority ──────────────────────────────────────────
SIGNAL_P0 = "P0"
SIGNAL_P1 = "P1"
SIGNAL_P2 = "P2"
SIGNAL_NONE = "NONE"

# ─── Announcement status ─────────────────────────────────────
ANN_STATUS_NEW = "NEW"
ANN_STATUS_PARSED = "PARSED"
ANN_STATUS_SIGNAL_MATCHED = "SIGNAL_MATCHED"
ANN_STATUS_NO_SIGNAL = "NO_SIGNAL"
ANN_STATUS_PARSE_FAILED = "PARSE_FAILED"

# ─── Rating levels ────────────────────────────────────────────
RATING_A = "A"   # >= 80
RATING_B = "B"   # >= 60
RATING_C = "C"   # >= 40
RATING_D = "D"   # < 40

# ─── Tracked target status ────────────────────────────────────
TARGET_OBSERVING = "OBSERVING"
TARGET_TRACKING = "TRACKING"
TARGET_REMOVED = "REMOVED"

# ─── Scan task ────────────────────────────────────────────────
TRIGGER_SCHEDULED = "SCHEDULED"
TRIGGER_MANUAL = "MANUAL"
TRIGGER_INCREMENTAL = "INCREMENTAL"

TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_COMPLETED = "COMPLETED"
TASK_STATUS_FAILED = "FAILED"
TASK_STATUS_CANCELLED = "CANCELLED"


def rating_from_score(score: float) -> str:
    if score >= 80:
        return RATING_A
    elif score >= 60:
        return RATING_B
    elif score >= 40:
        return RATING_C
    else:
        return RATING_D


# ─── Entities ─────────────────────────────────────────────────

@dataclass
class Announcement:
    """原始公告记录"""
    stock_code: str
    stock_name: str
    title: str
    publish_time: str              # ISO format
    event_type: str = EVENT_TYPE_UNKNOWN
    signal_priority: str = SIGNAL_NONE
    adjunct_url: Optional[str] = None
    adjunct_url_pdf: Optional[str] = None
    summary: Optional[str] = None
    status: str = ANN_STATUS_NEW
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now)


@dataclass
class ScreeningResult:
    """三阶段流水线的最终输出"""
    scan_task_id: str
    announcement_id: str
    stock_code: str
    stock_name: str
    announcement_title: str
    event_type: str
    signal_priority: str
    fundamental_score: float
    fundamental_detail: dict
    industry_score: float
    industry_detail: dict
    composite_rating: float
    rating_level: str
    report_md: str
    pseudo_signals: list = field(default_factory=list)
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now)

    def __post_init__(self):
        self.rating_level = rating_from_score(self.composite_rating)


@dataclass
class TrackedTarget:
    """用户跟踪的标的"""
    stock_code: str
    stock_name: str
    status: str = TARGET_OBSERVING
    removed_reason: Optional[str] = None
    notes: Optional[str] = None
    screening_result_ids: list = field(default_factory=list)
    id: str = field(default_factory=_new_id)
    added_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class ScanTask:
    """每次扫描执行记录"""
    trigger_type: str              # SCHEDULED / MANUAL / INCREMENTAL
    scan_from: str                 # "2026-06-01"
    scan_to: str                   # "2026-06-20"
    status: str = TASK_STATUS_PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    target_stocks: Optional[list] = None  # None = 全市场
    sector_filter: Optional[str] = None
    error_log: Optional[str] = None
    announcements_fetched: int = 0
    signals_matched: int = 0
    results_produced: int = 0
    task_meta: Optional[dict] = None
    id: str = field(default_factory=_new_id)
