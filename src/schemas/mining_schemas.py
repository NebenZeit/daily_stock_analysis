"""
潜力标的挖掘模块 — Pydantic 序列化 Schemas
用于 API 响应序列化和数据校验。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnnouncementSchema(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    title: str
    publish_time: str
    event_type: str
    signal_priority: str
    adjunct_url_pdf: Optional[str] = None
    summary: Optional[str] = None
    status: str = "NEW"
    created_at: str = ""


class ScreeningResultItem(BaseModel):
    """筛选结果列表项（轻量）"""
    id: str
    stock_code: str
    stock_name: str
    event_type: str
    signal_priority: str
    announcement_title: str
    fundamental_score: float
    industry_score: float
    composite_rating: float
    rating_level: str
    created_at: str
    tracked_status: Optional[str] = None


class FundamentalDetail(BaseModel):
    financial_health: float = 0
    governance: float = 0
    valuation_safety: float = 0
    details: dict[str, Any] = {}
    data_completeness: str = "none"


class IndustryDetail(BaseModel):
    sector_space: float = 0
    biz_synergy: float = 0
    industry_impact: float = 0
    earnings_elasticity: float = 0
    details: dict[str, Any] = {}


class ScreeningResultDetail(BaseModel):
    """筛选结果完整详情"""
    id: str
    stock_code: str
    stock_name: str
    event_type: str
    signal_priority: str
    announcement_title: str
    fundamental_score: float
    fundamental_detail: dict[str, Any] = {}
    industry_score: float
    industry_detail: dict[str, Any] = {}
    composite_rating: float
    rating_level: str
    pseudo_signals: list = []
    report_md: str = ""
    created_at: str
    task_id: Optional[str] = None
    announcement: Optional[AnnouncementSchema] = None


class ScreeningResultList(BaseModel):
    items: list[ScreeningResultItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ScanTaskSchema(BaseModel):
    id: str
    trigger_type: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    scan_from: str = ""
    scan_to: str = ""
    target_stocks: Optional[list[str]] = None
    sector_filter: Optional[str] = None
    error_log: Optional[str] = None
    announcements_fetched: int = 0
    signals_matched: int = 0
    results_produced: int = 0
    task_meta: Optional[dict] = None


class TrackedTargetSchema(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    status: str = "OBSERVING"
    added_at: str = ""
    updated_at: str = ""
    removed_reason: Optional[str] = None
    notes: Optional[str] = None


class SectorSchema(BaseModel):
    sector_id: str
    sector_name: str
    description: str = ""
    keywords: list[str] = []
    products: list[str] = []


class ScanRequest(BaseModel):
    since: Optional[str] = None
    until: Optional[str] = None
    target_stocks: Optional[list[str]] = None
    sector: Optional[str] = None
    board_type: str = "main_board"


class TargetStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(OBSERVING|TRACKING|REMOVED)$")
    reason: Optional[str] = None
