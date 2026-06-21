"""
潜力标的挖掘 — REST API 端点
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config import Config, get_config
from src.potential_stock_mining import run_potential_stock_mining
from src.potential_stock_mining.file_store import MiningFileStore
from src.potential_stock_mining.models import TRIGGER_MANUAL, TASK_STATUS_RUNNING
from src.schemas.mining_schemas import (
    ScreeningResultItem, ScreeningResultDetail, ScreeningResultList,
    ScanTaskSchema, TrackedTargetSchema, SectorSchema,
    ScanRequest, TargetStatusUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_store() -> MiningFileStore:
    return MiningFileStore()


# ── Scan ──────────────────────────────────────────────────────

@router.post("/scan", summary="手动触发挖掘扫描")
def trigger_scan(
    req: ScanRequest,
    config: Config = Depends(get_config),
):
    """手动触发潜力标的挖掘扫描"""
    store = _get_store()

    # Concurrency check
    running_id = store.has_running_task()
    if running_id:
        raise HTTPException(
            status_code=409,
            detail=f"已有扫描任务正在执行中（任务 ID: {running_id}），请等待完成后再试",
        )

    task = run_potential_stock_mining(
        since=req.since,
        until=req.until,
        trigger_type=TRIGGER_MANUAL,
        target_stocks=req.target_stocks,
        sector_filter=req.sector,
        board_type=req.board_type,
    )

    task_meta = task.task_meta or {}
    return {
        "task_id": task.id,
        "status": task.status,
        "message": "Scan completed",
        "results_produced": task.results_produced,
        "announcements_fetched": task.announcements_fetched,
        "signals_matched": task.signals_matched,
        "has_details": bool(task_meta.get("announcements")),
        "board_type": task_meta.get("board_type", "main_board"),
    }


# ── Results ───────────────────────────────────────────────────

@router.get("/results", summary="获取筛选结果列表")
def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str = Query("", description="事件类型过滤"),
    rating_level: str = Query("", description="评级等级过滤 A/B/C/D"),
    since: str = Query("", description="起始日期"),
    until: str = Query("", description="截止日期"),
    stock_code: str = Query("", description="指定标的"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
):
    store = _get_store()
    items, total = store.list_results(
        since=since, until=until,
        event_type=event_type, rating_level=rating_level,
        stock_code=stock_code,
        page=page, page_size=page_size,
    )

    # Build tracked status map
    targets = {t.stock_code: t.status for t in store.get_all_targets()}

    result_items = []
    for r in items:
        result_items.append(ScreeningResultItem(
            id=r.id,
            stock_code=r.stock_code,
            stock_name=r.stock_name,
            event_type=r.event_type,
            signal_priority=r.signal_priority,
            announcement_title=r.announcement_title,
            fundamental_score=r.fundamental_score,
            industry_score=r.industry_score,
            composite_rating=r.composite_rating,
            rating_level=r.rating_level,
            created_at=r.created_at,
            tracked_status=targets.get(r.stock_code),
        ))

    total_pages = max(1, (total + page_size - 1) // page_size)
    return ScreeningResultList(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/results/{result_id}", summary="获取筛选结果详情")
def get_result_detail(result_id: str):
    store = _get_store()
    result = store.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return ScreeningResultDetail(
        id=result.id,
        stock_code=result.stock_code,
        stock_name=result.stock_name,
        event_type=result.event_type,
        signal_priority=result.signal_priority,
        announcement_title=result.announcement_title,
        fundamental_score=result.fundamental_score,
        fundamental_detail=result.fundamental_detail,
        industry_score=result.industry_score,
        industry_detail=result.industry_detail,
        composite_rating=result.composite_rating,
        rating_level=result.rating_level,
        pseudo_signals=result.pseudo_signals,
        report_md=result.report_md,
        created_at=result.created_at,
    )


# ── Tasks ─────────────────────────────────────────────────────

@router.get("/tasks", summary="获取扫描任务列表")
def list_tasks(limit: int = Query(20, ge=1, le=100)):
    store = _get_store()
    tasks = store.list_tasks(limit=limit)
    return {
        "items": [
            ScanTaskSchema(
                id=t.id, trigger_type=t.trigger_type, status=t.status,
                started_at=t.started_at, completed_at=t.completed_at,
                scan_from=t.scan_from, scan_to=t.scan_to,
                target_stocks=t.target_stocks, sector_filter=t.sector_filter,
                error_log=t.error_log,
                announcements_fetched=t.announcements_fetched,
                signals_matched=t.signals_matched,
                results_produced=t.results_produced,
                task_meta=None,  # Omit full announcements in list view
            ) for t in tasks
        ],
        "total": len(tasks),
    }


@router.get("/tasks/{task_id}", summary="获取扫描任务详情")
def get_task_detail(task_id: str):
    store = _get_store()
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return ScanTaskSchema(
        id=task.id, trigger_type=task.trigger_type, status=task.status,
        started_at=task.started_at, completed_at=task.completed_at,
        scan_from=task.scan_from, scan_to=task.scan_to,
        target_stocks=task.target_stocks, sector_filter=task.sector_filter,
        error_log=task.error_log,
        announcements_fetched=task.announcements_fetched,
        signals_matched=task.signals_matched,
        results_produced=task.results_produced,
        task_meta=task.task_meta,
    )


# ── Targets ───────────────────────────────────────────────────

@router.get("/targets", summary="获取跟踪标的列表")
def list_targets():
    store = _get_store()
    targets = store.get_all_targets()
    return {
        "items": [
            TrackedTargetSchema(
                id=t.id, stock_code=t.stock_code, stock_name=t.stock_name,
                status=t.status, added_at=t.added_at, updated_at=t.updated_at,
                removed_reason=t.removed_reason, notes=t.notes,
            ) for t in targets
        ],
        "total": len(targets),
    }


@router.get("/targets/{stock_code}", summary="获取单个标的详情")
def get_target_detail(stock_code: str):
    store = _get_store()
    target = store.get_target(stock_code)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return TrackedTargetSchema(
        id=target.id, stock_code=target.stock_code, stock_name=target.stock_name,
        status=target.status, added_at=target.added_at, updated_at=target.updated_at,
        removed_reason=target.removed_reason, notes=target.notes,
    )


@router.put("/targets/{stock_code}/status", summary="更新标的跟踪状态")
def update_target_status(stock_code: str, req: TargetStatusUpdate):
    store = _get_store()
    target = store.get_target(stock_code)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    previous = target.status
    success = store.update_target_status(stock_code, req.status, req.reason or "")
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update status")

    return {
        "stock_code": stock_code,
        "previous_status": previous,
        "current_status": req.status,
        "updated_at": target.updated_at,
    }


# ── Sectors ───────────────────────────────────────────────────

@router.get("/sectors", summary="获取赛道列表")
def list_sectors():
    """从 industry_kb.yaml 读取赛道信息"""
    try:
        import yaml
        from pathlib import Path
        kb_path = Path("config/industry_kb.yaml")
        if kb_path.exists():
            data = yaml.safe_load(kb_path.read_text(encoding="utf-8"))
            sectors = data.get("sectors", {}) if isinstance(data, dict) else {}
            return {
                "items": [
                    SectorSchema(
                        sector_id=sid,
                        sector_name=info.get("sector_name", sid),
                        description=info.get("description", ""),
                        keywords=info.get("keywords", []),
                        products=info.get("products", []),
                    ) for sid, info in sectors.items()
                ],
                "total": len(sectors),
            }
    except Exception as e:
        logger.warning("Failed to load sectors: %s", e)
    return {"items": [], "total": 0}
