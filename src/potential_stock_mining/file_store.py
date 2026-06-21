"""
潜力标的智能挖掘系统 — JSON 文件化存储引擎

替代数据库/SQLAlchemy，所有数据以 JSON 文件存储。
目录结构:
  data/potential_stock_mining/
    index.json           — 汇总索引（按日期/stock_code 快速定位）
    tasks/               — 扫描任务文件 {task_id}.json
    results/YYYY/MM/     — 按月组织的筛选结果 {result_id}.json
    targets.json         — 跟踪标的清单（单一文件）
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import (
    Announcement, ScreeningResult, ScanTask, TrackedTarget,
    TARGET_OBSERVING, TARGET_TRACKING, TARGET_REMOVED,
    TASK_STATUS_PENDING, TASK_STATUS_RUNNING, TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED, TASK_STATUS_CANCELLED,
)

logger = logging.getLogger(__name__)


class MiningFileStore:
    """JSON 文件化存储引擎"""

    DATA_DIR = "data/potential_stock_mining"

    def __init__(self, data_dir: Optional[str] = None):
        self._lock = threading.Lock()
        self._data_dir = Path(data_dir or self.DATA_DIR)
        self._ensure_dirs()

    # ── Path helpers ──────────────────────────────────────────

    def _ensure_dirs(self):
        dirs = [
            self._data_dir,
            self._data_dir / "tasks",
            self._data_dir / "results",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _result_path(self, result_id: str, dt: date) -> Path:
        ym = self._data_dir / "results" / f"{dt.year}" / f"{dt.month:02d}"
        ym.mkdir(parents=True, exist_ok=True)
        return ym / f"{result_id}.json"

    def _task_path(self, task_id: str) -> Path:
        return self._data_dir / "tasks" / f"{task_id}.json"

    def _targets_path(self) -> Path:
        return self._data_dir / "targets.json"

    def _index_path(self) -> Path:
        return self._data_dir / "index.json"

    # ── Internal read/write ───────────────────────────────────

    def _read_json(self, path: Path) -> Optional[dict]:
        try:
            if path.exists() and path.stat().st_size > 0:
                return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", path, e)
        return None

    def _write_json(self, path: Path, data: dict) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except OSError as e:
            logger.error("Failed to write %s: %s", path, e)
            return False

    # ── Index ─────────────────────────────────────────────────

    def _load_index(self) -> dict:
        idx = self._read_json(self._index_path()) or {}
        for key in ("results", "tasks"):
            idx.setdefault(key, {})
        return idx

    def _save_index(self, idx: dict) -> bool:
        return self._write_json(self._index_path(), idx)

    def _rebuild_index(self) -> None:
        """全量重建索引，从文件系统扫描所有结果和任务"""
        idx = {"results": {}, "tasks": {}}
        # Scan results
        results_dir = self._data_dir / "results"
        if results_dir.exists():
            for year_dir in results_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for f in month_dir.glob("*.json"):
                        data = self._read_json(f)
                        if data:
                            key = f"{year_dir.name}-{month_dir.name}"
                            idx["results"].setdefault(key, [])
                            idx["results"][key].append({
                                "id": data.get("id"),
                                "stock_code": data.get("stock_code"),
                                "event_type": data.get("event_type"),
                                "created_at": data.get("created_at"),
                            })
        # Scan tasks
        tasks_dir = self._data_dir / "tasks"
        if tasks_dir.exists():
            for f in sorted(tasks_dir.glob("*.json"), reverse=True):
                data = self._read_json(f)
                if data:
                    idx["tasks"][data["id"]] = {
                        "trigger_type": data.get("trigger_type"),
                        "status": data.get("status"),
                        "started_at": data.get("started_at"),
                    }
        self._save_index(idx)

    # ── ScreenResult CRUD ─────────────────────────────────────

    def save_result(self, result: ScreeningResult) -> str:
        """保存筛选结果，返回 result_id"""
        with self._lock:
            created = datetime.fromisoformat(result.created_at)
            path = self._result_path(result.id, created.date())
            self._write_json(path, _result_to_dict(result))
            # Update index
            idx = self._load_index()
            key = f"{created.year}-{created.month:02d}"
            idx["results"].setdefault(key, [])
            # Dedup by id in index
            idx["results"][key] = [
                e for e in idx["results"][key] if e.get("id") != result.id
            ]
            idx["results"][key].append({
                "id": result.id,
                "stock_code": result.stock_code,
                "event_type": result.event_type,
                "rating_level": result.rating_level,
                "composite_rating": result.composite_rating,
                "created_at": result.created_at,
            })
            self._save_index(idx)
        return result.id

    def get_result(self, result_id: str) -> Optional[ScreeningResult]:
        """按 ID 获取筛选结果"""
        idx = self._load_index()
        for key, entries in idx.get("results", {}).items():
            for e in entries:
                if e.get("id") == result_id:
                    year, month = key.split("-")
                    path = self._data_dir / "results" / year / month / f"{result_id}.json"
                    data = self._read_json(path)
                    if data:
                        return _dict_to_result(data)
                    return None
        return None

    def list_results(
        self,
        since: str = "",
        until: str = "",
        event_type: str = "",
        rating_level: str = "",
        stock_code: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ScreeningResult], int]:
        """列出筛选结果，支持分页和筛选"""
        idx = self._load_index()
        all_results: list[ScreeningResult] = []
        seen_ids = set()

        for key, entries in idx.get("results", {}).items():
            year_str, month_str = key.split("-")
            year_dir = self._data_dir / "results" / year_str / month_str
            if not year_dir.exists():
                continue
            for entry in entries:
                rid = entry.get("id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    path = year_dir / f"{rid}.json"
                    data = self._read_json(path)
                    if data:
                        sr = _dict_to_result(data)
                        if self._match_filters(sr, since, until, event_type, rating_level, stock_code):
                            all_results.append(sr)

        # Sort by created_at desc
        all_results.sort(key=lambda r: r.created_at, reverse=True)

        total = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size
        return all_results[start:end], total

    def _match_filters(
        self, r: ScreeningResult,
        since: str, until: str,
        event_type: str, rating_level: str, stock_code: str,
    ) -> bool:
        if event_type and r.event_type != event_type:
            return False
        if rating_level and r.rating_level != rating_level:
            return False
        if stock_code and r.stock_code != stock_code:
            return False
        if since and r.created_at < since:
            return False
        if until and r.created_at > until:
            return False
        return True

    def delete_result(self, result_id: str) -> bool:
        """删除筛选结果"""
        with self._lock:
            idx = self._load_index()
            for key, entries in list(idx.get("results", {}).items()):
                for e in list(entries):
                    if e.get("id") == result_id:
                        entries.remove(e)
                        year, month = key.split("-")
                        path = self._data_dir / "results" / year / month / f"{result_id}.json"
                        if path.exists():
                            path.unlink()
                        self._save_index(idx)
                        return True
        return False

    # ── ScanTask CRUD ─────────────────────────────────────────

    def save_task(self, task: ScanTask) -> str:
        path = self._task_path(task.id)
        self._write_json(path, _task_to_dict(task))
        # Update task index
        idx = self._load_index()
        idx["tasks"][task.id] = {
            "trigger_type": task.trigger_type,
            "status": task.status,
            "started_at": task.started_at,
        }
        self._save_index(idx)
        return task.id

    def get_task(self, task_id: str) -> Optional[ScanTask]:
        path = self._task_path(task_id)
        data = self._read_json(path)
        if data:
            return _dict_to_task(data)
        return None

    def list_tasks(self, limit: int = 20) -> list[ScanTask]:
        idx = self._load_index()
        tasks = []
        for tid, info in idx.get("tasks", {}).items():
            path = self._task_path(tid)
            data = self._read_json(path)
            if data:
                tasks.append(_dict_to_task(data))
        tasks.sort(key=lambda t: t.started_at or "", reverse=True)
        return tasks[:limit]

    def has_running_task(self) -> Optional[str]:
        """检查是否有运行中的任务，返回任务 ID 或 None"""
        idx = self._load_index()
        for tid, info in idx.get("tasks", {}).items():
            if info.get("status") == TASK_STATUS_RUNNING:
                return tid
        return None

    # ── TrackedTarget CRUD ────────────────────────────────────

    def _load_targets(self) -> list[TrackedTarget]:
        data_list = self._read_json(self._targets_path())
        if not data_list:
            return []
        return [_dict_to_target(d) for d in data_list]

    def _save_targets(self, targets: list[TrackedTarget]) -> bool:
        return self._write_json(
            self._targets_path(),
            [_target_to_dict(t) for t in targets]
        )

    def get_all_targets(self) -> list[TrackedTarget]:
        return self._load_targets()

    def get_target(self, stock_code: str) -> Optional[TrackedTarget]:
        for t in self._load_targets():
            if t.stock_code == stock_code:
                return t
        return None

    def save_target(self, target: TrackedTarget) -> str:
        with self._lock:
            targets = self._load_targets()
            for i, t in enumerate(targets):
                if t.stock_code == target.stock_code:
                    targets[i] = target
                    break
            else:
                targets.append(target)
            self._save_targets(targets)
        return target.id

    def update_target_status(
        self, stock_code: str, status: str, reason: str = ""
    ) -> bool:
        from datetime import datetime, timezone
        valid = {TARGET_OBSERVING, TARGET_TRACKING, TARGET_REMOVED}
        if status not in valid:
            logger.warning("Invalid target status: %s", status)
            return False
        with self._lock:
            targets = self._load_targets()
            for t in targets:
                if t.stock_code == stock_code:
                    t.status = status
                    t.updated_at = datetime.now(timezone.utc).isoformat()
                    if status == TARGET_REMOVED and reason:
                        t.removed_reason = reason
                    self._save_targets(targets)
                    return True
        return False

    def update_target_notes(self, stock_code: str, notes: str) -> bool:
        from datetime import datetime, timezone
        with self._lock:
            targets = self._load_targets()
            for t in targets:
                if t.stock_code == stock_code:
                    t.notes = notes
                    t.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save_targets(targets)
                    return True
        return False


# ── Serialization helpers ─────────────────────────────────────

def _result_to_dict(r: ScreeningResult) -> dict:
    return {
        "id": r.id,
        "scan_task_id": r.scan_task_id,
        "announcement_id": r.announcement_id,
        "stock_code": r.stock_code,
        "stock_name": r.stock_name,
        "announcement_title": r.announcement_title,
        "event_type": r.event_type,
        "signal_priority": r.signal_priority,
        "fundamental_score": r.fundamental_score,
        "fundamental_detail": r.fundamental_detail,
        "industry_score": r.industry_score,
        "industry_detail": r.industry_detail,
        "composite_rating": r.composite_rating,
        "rating_level": r.rating_level,
        "pseudo_signals": r.pseudo_signals,
        "report_md": r.report_md,
        "created_at": r.created_at,
    }


def _dict_to_result(d: dict) -> ScreeningResult:
    return ScreeningResult(
        id=d.get("id", ""),
        scan_task_id=d.get("scan_task_id", ""),
        announcement_id=d.get("announcement_id", ""),
        stock_code=d.get("stock_code", ""),
        stock_name=d.get("stock_name", ""),
        announcement_title=d.get("announcement_title", ""),
        event_type=d.get("event_type", ""),
        signal_priority=d.get("signal_priority", ""),
        fundamental_score=d.get("fundamental_score", 0.0),
        fundamental_detail=d.get("fundamental_detail", {}),
        industry_score=d.get("industry_score", 0.0),
        industry_detail=d.get("industry_detail", {}),
        composite_rating=d.get("composite_rating", 0.0),
        rating_level=d.get("rating_level", "D"),
        pseudo_signals=d.get("pseudo_signals", []),
        report_md=d.get("report_md", ""),
        created_at=d.get("created_at", ""),
    )


def _task_to_dict(t: ScanTask) -> dict:
    return {
        "id": t.id,
        "trigger_type": t.trigger_type,
        "status": t.status,
        "started_at": t.started_at,
        "completed_at": t.completed_at,
        "scan_from": t.scan_from,
        "scan_to": t.scan_to,
        "target_stocks": t.target_stocks,
        "sector_filter": t.sector_filter,
        "error_log": t.error_log,
        "announcements_fetched": t.announcements_fetched,
        "signals_matched": t.signals_matched,
        "results_produced": t.results_produced,
        "task_meta": t.task_meta,
    }


def _dict_to_task(d: dict) -> ScanTask:
    return ScanTask(
        id=d.get("id", ""),
        trigger_type=d.get("trigger_type", ""),
        status=d.get("status", "PENDING"),
        started_at=d.get("started_at"),
        completed_at=d.get("completed_at"),
        scan_from=d.get("scan_from", ""),
        scan_to=d.get("scan_to", ""),
        target_stocks=d.get("target_stocks"),
        sector_filter=d.get("sector_filter"),
        error_log=d.get("error_log"),
        announcements_fetched=d.get("announcements_fetched", 0),
        signals_matched=d.get("signals_matched", 0),
        results_produced=d.get("results_produced", 0),
        task_meta=d.get("task_meta"),
    )


def _target_to_dict(t: TrackedTarget) -> dict:
    return {
        "id": t.id,
        "stock_code": t.stock_code,
        "stock_name": t.stock_name,
        "status": t.status,
        "added_at": t.added_at,
        "updated_at": t.updated_at,
        "removed_reason": t.removed_reason,
        "notes": t.notes,
        "screening_result_ids": t.screening_result_ids,
    }


def _dict_to_target(d: dict) -> TrackedTarget:
    return TrackedTarget(
        id=d.get("id", ""),
        stock_code=d.get("stock_code", ""),
        stock_name=d.get("stock_name", ""),
        status=d.get("status", TARGET_OBSERVING),
        added_at=d.get("added_at", ""),
        updated_at=d.get("updated_at", ""),
        removed_reason=d.get("removed_reason"),
        notes=d.get("notes"),
        screening_result_ids=d.get("screening_result_ids", []),
    )
