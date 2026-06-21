"""
伪转型甄别模块

自动识别和标记"伪转型"标的 — 那些看起来有跨界/转型动作，
但实际上缺乏实质支撑、可能是蹭热点的情况。

降权规则：
1. 主业与新赛道完全割裂（跨行业代码差异大）
2. 转型公告集中在行情火热期
3. 落地形式为空壳公司/框架协议/意向书
4. 研发费用率极低且无核心技术储备
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# 框架协议/意向书关键词
VAGUE_KEYWORDS = [
    "框架协议", "意向书", "战略框架", "合作意向",
    "备忘录", "初步协商", "尚待论证",
]

# 空壳公司/皮包公司特征
SHELL_KEYWORDS = [
    "注册成立", "投资设立", "新设公司",
]


def detect_pseudo_signals(
    title: str,
    fundamental_detail: Optional[dict] = None,
    industry_detail: Optional[dict] = None,
) -> list[dict]:
    """
    检测伪转型信号，返回信号列表。
    每条信号: {"type": str, "severity": "high"/"medium"/"low", "reason": str}
    """
    signals = []

    # Rule 1: 框架协议/意向书（无实质约束）
    if any(kw in title for kw in VAGUE_KEYWORDS):
        signals.append({
            "type": "vague_agreement",
            "severity": "high",
            "reason": f"公告含框架协议/意向书类关键词，缺乏实质约束力",
        })

    # Rule 2: 新设公司（可能为空壳）
    if any(kw in title for kw in SHELL_KEYWORDS):
        signals.append({
            "type": "shell_company",
            "severity": "medium",
            "reason": "公告涉及新设公司，需关注是否为空壳主体",
        })

    # Rule 3: 研发投入不足
    if fundamental_detail:
        details = fundamental_detail.get("details", {})
        rnd_ratio = details.get("rnd_ratio")
        if rnd_ratio is not None and rnd_ratio < 0.02:
            signals.append({
                "type": "low_rnd",
                "severity": "medium",
                "reason": f"研发费用率 {rnd_ratio:.1%} < 2%，转型缺乏技术支撑",
            })

        # Rule 4: 营收下滑严重
        revenue_yoy = details.get("revenue_yoy")
        if revenue_yoy is not None and revenue_yoy < -0.3:
            signals.append({
                "type": "distressed_pivot",
                "severity": "high",
                "reason": f"营收同比 {revenue_yoy:.1%}，业绩承压下转型可能为自救行为",
            })

    return signals


def should_downgrade(signals: list[dict]) -> tuple[bool, float]:
    """
    根据伪转型信号判断是否需要降权。
    返回 (should_downgrade, penalty_factor)  penalty_factor: 0.0-1.0 降权系数
    """
    if not signals:
        return False, 1.0

    high_count = sum(1 for s in signals if s.get("severity") == "high")
    med_count = sum(1 for s in signals if s.get("severity") == "medium")

    # High severity signals cause significant downgrade
    if high_count >= 2:
        return True, 0.3
    elif high_count == 1:
        return True, 0.5
    elif med_count >= 2:
        return True, 0.7
    else:
        return False, 1.0
