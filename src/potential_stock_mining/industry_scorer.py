"""
产业增量价值评分引擎

对通过基本面过滤的标的进行 4 维度产业价值评估：
1. 赛道空间（30%）— 市场规模、增速、渗透率
2. 业务协同性（25%）— 与主业关联度、技术共享度
3. 行业格局影响（20%）— 竞争格局变化、先发优势
4. 业绩弹性（25%）— 营收占比、利润率影响

评分范围 0-100，最终 industry_score = 各维度加权和。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# 维度配置
DIMENSION_WEIGHTS = {
    "sector_space": 0.30,
    "biz_synergy": 0.25,
    "industry_impact": 0.20,
    "earnings_elasticity": 0.25,
}


def score_industry(
    fundamental_detail: Optional[dict] = None,
    industry_detail: Optional[dict] = None,
) -> tuple[float, dict]:
    """
    评估产业增量价值，返回 (industry_score, detail_dict)。

    industry_detail 预期结构:
    {
        "sector_name": str,
        "sector_growth_rate": float,
        "estimated_market_size": str,
        "target_revenue_ratio": float,
    }

    fundamental_detail 预期结构:
    {
        "details": {
            "revenue_yoy": float,
            "gross_margin": float,
            ...
        }
    }
    """
    idetail = industry_detail or {}
    fdetail = fundamental_detail or {}
    fdetails = fdetail.get("details", {})

    # --- 赛道空间评分 ---
    growth_rate = idetail.get("sector_growth_rate", 0)
    sector_space = _score_sector_space(growth_rate)

    # --- 业务协同性评分 ---
    # 基于基本面中毛利率和营收增速反推协同性
    gross_margin = fdetails.get("gross_margin", 0)
    revenue_yoy = fdetails.get("revenue_yoy", 0)
    biz_synergy = _score_biz_synergy(gross_margin, revenue_yoy)

    # --- 行业格局影响评分 ---
    # 高增速赛道通常格局未定，新进入者机会更大
    industry_impact = _score_industry_impact(growth_rate)

    # --- 业绩弹性评分 ---
    target_ratio = idetail.get("target_revenue_ratio", 0)
    earnings_elasticity = _score_earnings_elasticity(target_ratio, gross_margin)

    # --- 加权综合 ---
    raw = (
        sector_space * DIMENSION_WEIGHTS["sector_space"]
        + biz_synergy * DIMENSION_WEIGHTS["biz_synergy"]
        + industry_impact * DIMENSION_WEIGHTS["industry_impact"]
        + earnings_elasticity * DIMENSION_WEIGHTS["earnings_elasticity"]
    )

    score = round(min(max(raw, 0), 100), 1)
    detail = {
        "sector_space": sector_space,
        "biz_synergy": biz_synergy,
        "industry_impact": industry_impact,
        "earnings_elasticity": earnings_elasticity,
        "weights": DIMENSION_WEIGHTS,
    }
    return score, detail


def _score_sector_space(growth_rate: float) -> float:
    """赛道空间评分：高增速赛道得分高"""
    if growth_rate >= 0.30:
        return 90
    elif growth_rate >= 0.20:
        return 75
    elif growth_rate >= 0.10:
        return 60
    elif growth_rate >= 0.05:
        return 45
    elif growth_rate >= 0:
        return 30
    else:
        return 20


def _score_biz_synergy(gross_margin: float, revenue_yoy: float) -> float:
    """业务协同性评分：高毛利 + 稳健增长的公司更可能成功跨界"""
    score = 50  # baseline

    if gross_margin >= 0.40:
        score += 20
    elif gross_margin >= 0.25:
        score += 10
    elif gross_margin < 0.10:
        score -= 10

    if revenue_yoy >= 0.20:
        score += 15
    elif revenue_yoy >= 0.05:
        score += 5
    elif revenue_yoy < -0.10:
        score -= 10

    return min(max(score, 0), 100)


def _score_industry_impact(growth_rate: float) -> float:
    """行业格局影响评分"""
    if growth_rate >= 0.25:
        return 70  # 高增速赛道格局未定，新玩家机会大
    elif growth_rate >= 0.15:
        return 60
    elif growth_rate >= 0.05:
        return 50
    else:
        return 40


def _score_earnings_elasticity(target_ratio: float, gross_margin: float) -> float:
    """业绩弹性评分：新业务占比越大，对整体业绩影响越大"""
    if target_ratio >= 0.30:
        base = 80
    elif target_ratio >= 0.15:
        base = 65
    elif target_ratio >= 0.05:
        base = 50
    else:
        base = 30

    # 高毛利业务弹性更大
    if gross_margin >= 0.40:
        base += 10
    elif gross_margin < 0.15:
        base -= 10

    return min(max(base, 0), 100)
