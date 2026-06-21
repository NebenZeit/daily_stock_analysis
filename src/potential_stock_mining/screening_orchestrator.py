"""
三阶段流水线编排器

串联公告获取 → 信号识别 → 基本面过滤 → 产业价值评分 → 报告生成
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .models import (
    Announcement, ScreeningResult, ScanTask,
    EVENT_TYPE_M_A, EVENT_TYPE_CAP_EXPAND, EVENT_TYPE_BIZ_CHANGE,
    EVENT_TYPE_TECH_COOP, EVENT_TYPE_ORDER,
    TASK_STATUS_PENDING, TASK_STATUS_RUNNING, TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED, TASK_STATUS_CANCELLED,
    TRIGGER_SCHEDULED, TRIGGER_MANUAL, TRIGGER_INCREMENTAL,
)
from .file_store import MiningFileStore
from .announcement_fetcher import fetch_announcements, BOARD_MAIN
from .signal_identifier import batch_identify, _load_keywords
from .fundamental_filter import filter_stock
from .industry_scorer import score_industry
from .pseudo_transformation import detect_pseudo_signals, should_downgrade
from .report_generator import generate_report
from .rule_engine import load_rules, evaluate_fundamental_rules

logger = logging.getLogger(__name__)

# 事件类型优先级排序
EVENT_PRIORITY_ORDER = {
    EVENT_TYPE_M_A: 0,
    EVENT_TYPE_CAP_EXPAND: 1,
    EVENT_TYPE_BIZ_CHANGE: 2,
    EVENT_TYPE_TECH_COOP: 3,
    EVENT_TYPE_ORDER: 4,
}


class ScreeningOrchestrator:
    """三阶段流水线编排器"""

    def __init__(
        self,
        file_store: Optional[MiningFileStore] = None,
    ):
        self.file_store = file_store or MiningFileStore()
        self.keywords_config = _load_keywords()
        self.rules = load_rules()

    def run_scan(
        self,
        scan_from: str,
        scan_to: str,
        trigger_type: str = TRIGGER_MANUAL,
        target_stocks: Optional[list[str]] = None,
        sector_filter: Optional[str] = None,
        board_type: str = BOARD_MAIN,
    ) -> ScanTask:
        """
        执行一次完整扫描。

        Args:
            scan_from: 扫描起始日期 "2026-06-01"
            scan_to: 扫描截止日期 "2026-06-20"
            trigger_type: SCHEDULED / MANUAL / INCREMENTAL
            target_stocks: 指定标的列表（None=全市场）
            sector_filter: 赛道过滤（None=全部）
            board_type: 板块过滤 main_board（仅主板）/ all（全市场）

        Returns:
            更新后的 ScanTask（已完成或失败）
        """
        task = ScanTask(
            trigger_type=trigger_type,
            scan_from=scan_from,
            scan_to=scan_to,
            target_stocks=target_stocks,
            sector_filter=sector_filter,
            status=TASK_STATUS_RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        # 在 task_meta 中记录扫描参数
        task.task_meta = {"board_type": board_type}
        self.file_store.save_task(task)

        try:
            results = self._execute_pipeline(task)
            task.status = TASK_STATUS_COMPLETED
            task.results_produced = len(results)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self.file_store.save_task(task)
        except Exception as e:
            logger.exception("Scan task %s failed", task.id)
            task.status = TASK_STATUS_FAILED
            task.error_log = str(e)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self.file_store.save_task(task)

        return task

    def _execute_pipeline(self, task: ScanTask) -> list[ScreeningResult]:
        """
        执行三阶段流水线：
        Phase 1: 公告获取
        Phase 2: 信号识别 + 基本面过滤
        Phase 3: 产业评分 + 报告生成
        """
        # ── Phase 1: 获取公告 ─────────────────────────────────
        logger.info(
            "Phase 1: Fetching announcements %s ~ %s",
            task.scan_from, task.scan_to,
        )

        # 从 task_meta 中读取板块过滤参数，默认 main_board
        board_type = (task.task_meta or {}).get("board_type", BOARD_MAIN)

        announcements = fetch_announcements(
            scan_from=task.scan_from,
            scan_to=task.scan_to,
            stock_codes=task.target_stocks,
            board_type=board_type,
        )
        task.announcements_fetched = len(announcements)
        logger.info("Fetched %d announcements", len(announcements))

        if not announcements:
            logger.info("No announcements found, scan complete")
            return []

        # ── Phase 2: 信号识别 ─────────────────────────────────
        logger.info("Phase 2: Signal identification")
        identified = batch_identify(announcements, self.keywords_config)
        matched = [a for a in identified if a.status == "SIGNAL_MATCHED"]
        task.signals_matched = len(matched)
        logger.info("Signals matched: %d", len(matched))

        # Save all announcements (with signal status) to task meta for frontend display
        task.task_meta = {
            **(task.task_meta or {}),
            "announcements": [
                {
                    "id": a.id,
                    "stock_code": a.stock_code,
                    "stock_name": a.stock_name,
                    "title": a.title,
                    "publish_time": a.publish_time,
                    "event_type": a.event_type,
                    "signal_priority": a.signal_priority,
                    "status": a.status,
                }
                for a in identified
            ],
        }
        self.file_store.save_task(task)

        if not matched:
            logger.info("No signals matched, scan complete")
            return []

        # ── Phase 2b: 基本面过滤 ──────────────────────────────
        logger.info("Phase 2b: Fundamental filtering")
        passed_fundamental = []
        for ann in matched:
            passes, score, detail = filter_stock(ann.stock_code)
            if passes:
                passed_fundamental.append((ann, score, detail))
            else:
                logger.debug("Stock %s failed fundamental filter", ann.stock_code)

        logger.info("Passed fundamental filter: %d/%d", len(passed_fundamental), len(matched))

        if not passed_fundamental:
            return []

        # ── Phase 3: 产业评分 + 伪转型检测 + 报告生成 ──────────
        logger.info("Phase 3: Industry scoring & report generation")
        results = []
        for ann, fund_score, fund_detail in passed_fundamental:
            # Industry scoring
            ind_score, ind_detail = score_industry(
                fundamental_detail=fund_detail,
            )

            # Pseudo transformation detection
            pseudo = detect_pseudo_signals(
                title=ann.title,
                fundamental_detail=fund_detail,
                industry_detail=ind_detail,
            )
            _, penalty = should_downgrade(pseudo)

            # Apply pseudo penalty to industry score
            ind_score = round(ind_score * penalty, 1)

            # Composite rating (50% fundamental + 50% industry)
            composite = round(fund_score * 0.5 + ind_score * 0.5, 1)

            # Generate report
            screening_result = ScreeningResult(
                scan_task_id=task.id,
                announcement_id=ann.id,
                stock_code=ann.stock_code,
                stock_name=ann.stock_name,
                announcement_title=ann.title,
                event_type=ann.event_type,
                signal_priority=ann.signal_priority,
                fundamental_score=fund_score,
                fundamental_detail=fund_detail,
                industry_score=ind_score,
                industry_detail=ind_detail,
                composite_rating=composite,
                rating_level="D",  # Will be set by __post_init__
                report_md="",
                pseudo_signals=pseudo,
            )
            # Generate report after composite is set
            screening_result.report_md = generate_report(screening_result)

            # Save
            self.file_store.save_result(screening_result)
            results.append(screening_result)

        # Sort results by priority
        results.sort(key=lambda r: (
            EVENT_PRIORITY_ORDER.get(r.event_type, 99),
            -r.composite_rating,
        ))

        logger.info("Pipeline complete: %d results", len(results))
        return results
