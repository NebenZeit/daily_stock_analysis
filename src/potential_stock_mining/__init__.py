"""
潜力标的智能挖掘系统

基于 A 股公告事件、基本面、产业增量价值的自动化标的筛选子系统。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .announcement_fetcher import BOARD_MAIN, BOARD_ALL
from .file_store import MiningFileStore
from .screening_orchestrator import ScreeningOrchestrator
from .models import ScanTask, TRIGGER_SCHEDULED, TRIGGER_MANUAL

logger = logging.getLogger(__name__)


def run_potential_stock_mining(
    since: Optional[str] = None,
    until: Optional[str] = None,
    trigger_type: str = TRIGGER_MANUAL,
    target_stocks: Optional[list[str]] = None,
    sector_filter: Optional[str] = None,
    board_type: str = BOARD_MAIN,
) -> ScanTask:
    """
    执行潜力标的挖掘扫描。

    默认范围（未指定 since/until）：
      - 首次运行：近 30 天
      - 后续运行：最近一个交易日
    可通过 --since / --until 参数覆盖。

    Args:
        since: 扫描起始日期 "2026-06-01"（None=自动）
        until: 扫描截止日期 "2026-06-20"（None=自动）
        trigger_type: 触发方式
        target_stocks: 指定标的列表（None=全市场扫描所有主板A股）
        sector_filter: 赛道过滤
        board_type: 板块过滤 main_board（仅主板A股）/ all（全市场含创业板科创板）

    Returns:
        完成后的 ScanTask
    """
    # Auto-calculate date range
    today = date.today()
    if until is None:
        until = today.isoformat()

    if since is None:
        since = (today - timedelta(days=30)).isoformat()

    logger.info(
        "Starting scan: %s ~ %s (trigger=%s, stocks=%s, sector=%s)",
        since, until, trigger_type,
        target_stocks or "all",
        sector_filter or "all",
    )

    file_store = MiningFileStore()
    orchestrator = ScreeningOrchestrator(file_store=file_store)

    task = orchestrator.run_scan(
        scan_from=since,
        scan_to=until,
        trigger_type=trigger_type,
        target_stocks=target_stocks,
        sector_filter=sector_filter,
        board_type=board_type,
    )

    # Log summary
    logger.info("===== 潜力标的挖掘结果 =====")
    logger.info("[scan] 扫描范围: %s ~ %s", since, until)
    logger.info("[scan] 共扫描 %d 条公告，命中 %d 个信号",
                task.announcements_fetched, task.signals_matched)

    if task.results_produced > 0:
        results = file_store.list_results(since=since, until=until)
        if results[0]:
            grouped = {}
            for r in results[0]:
                pri = r.signal_priority
                grouped.setdefault(pri, []).append(r)

            for pri in ["P0", "P1", "P2"]:
                items = grouped.get(pri, [])
                if items:
                    event_cn = items[0].event_type
                    logger.info("[scan] 【%s】%s（%d条）", pri, event_cn, len(items))
                    for r in items:
                        title = r.announcement_title[:50]
                        logger.info("[scan] %s %s — %s（评分 %s/100）",
                                    r.stock_code, r.stock_name, title, r.composite_rating)
    else:
        logger.info("[scan] 当日无新增潜力标的。")

    if task.error_log:
        logger.warning("[scan] 扫描出现错误: %s", task.error_log)

    # ── 通知推送 ─────────────────────────────────────────────
    _send_notification_if_enabled(task, since, until)

    return task


def _send_notification_if_enabled(task: ScanTask, since: str, until: str):
    """推送扫描结果通知（如配置启用）"""
    try:
        from src.config import get_config
        config = get_config()
        if not getattr(config, 'potential_stock_notify_enabled', False):
            return

        from src.notification import NotificationService
        notifier = NotificationService(config)

        lines = [f"📊 潜力标的扫描简报 ({since} ~ {until})"]
        lines.append(f"扫描公告: {task.announcements_fetched} 条 | 命中信号: {task.signals_matched}")

        if task.results_produced > 0:
            lines.append(f"\n新增潜力标的 ({task.results_produced} 条):\n")
            from .file_store import MiningFileStore
            store = MiningFileStore()
            results = store.list_results(since=since, until=until)
            if results[0]:
                for r in results[0]:
                    lines.append(f"- [{r.rating_level}] {r.stock_code} {r.stock_name}: {r.announcement_title[:60]} ({r.composite_rating}分)")
        else:
            lines.append("\n当日无新增潜力标的。")

        if task.error_log:
            lines.append(f"\n⚠️ 错误: {task.error_log}")

        message = "\n".join(lines)
        if notifier.is_available():
            notifier.send(message, route_type="report")
            logger.info("已推送潜力标的扫描简报")
    except Exception as e:
        logger.warning("推送潜力标的通知失败: %s", e)
