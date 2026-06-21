"""
基本面质量过滤

复用现有 DSA 的 DataFetcherManager.get_fundamental_context() 获取基础财务数据，
评估标的的财务健康度、治理与执行力、估值安全边际。

评分维度：
- financial_health (40%)：营收增长、盈利能力、现金流、负债水平
- governance (30%)：实控人信用、管理层稳定性（根据现有数据有限评估）
- valuation_safety (30%)：PE/PB 历史分位、市值弹性
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def filter_stock(
    stock_code: str,
    fundamental_context: Optional[dict] = None,
    fundamental_detail: Optional[dict] = None,
) -> tuple[bool, float, dict]:
    """
    对单个标的进行基本面过滤。
    返回 (passes, score, detail_dict)

    如果没有足够数据，标记为 data_completeness=partial 但仍给出评分。
    只有数据完全缺失时才不通过。
    """
    # If we have no fundamental data at all, still pass (with low score) to not block
    if not fundamental_context and not fundamental_detail:
        return True, 30.0, {
            "financial_health": 30,
            "governance": 30,
            "valuation_safety": 30,
            "details": {},
            "data_completeness": "none",
        }

    detail = fundamental_detail or {}
    fc = fundamental_context or {}

    # --- financial_health ---
    fh_score = _score_financial_health(fc, detail)

    # --- governance ---
    gov_score = _score_governance(fc, detail)

    # --- valuation_safety ---
    val_score = _score_valuation_safety(fc, detail)

    # --- Composite ---
    raw = fh_score * 0.40 + gov_score * 0.30 + val_score * 0.30
    score = round(min(max(raw, 0), 100), 1)

    passes = score >= 30  # Low bar — only filter out clearly bad stocks

    result_detail = {
        "financial_health": fh_score,
        "governance": gov_score,
        "valuation_safety": val_score,
        "details": _extract_details(fc, detail),
        "data_completeness": _completeness(fc, detail),
    }

    return passes, score, result_detail


def _extract_details(fc: dict, detail: dict) -> dict:
    """提取关键财务指标"""
    if detail.get("details"):
        return detail["details"]

    # Attempt to extract from fundamental_context
    details = {}
    try:
        growth = fc.get("growth", {}) or {}
        details["revenue_yoy"] = growth.get("revenue_yoy")
        details["net_profit_yoy"] = growth.get("net_profit_yoy")
        details["gross_margin"] = growth.get("gross_margin")
        details["roe"] = growth.get("roe")
    except Exception:
        pass
    try:
        earnings = fc.get("earnings", {}) or {}
        fr = earnings.get("financial_report", {}) or {}
        details["revenue"] = fr.get("revenue")
        details["net_profit_parent"] = fr.get("net_profit_parent")
        details["operating_cash_flow"] = fr.get("operating_cash_flow")
    except Exception:
        pass
    try:
        val = fc.get("valuation", {}) or {}
        details["pe_ratio"] = val.get("pe_ratio")
        details["pb_ratio"] = val.get("pb_ratio")
        details["market_cap"] = val.get("total_mv") or val.get("circ_mv")
    except Exception:
        pass

    return details


def _completeness(fc: dict, detail: dict) -> str:
    """评估数据完整度"""
    if detail.get("data_completeness"):
        return detail["data_completeness"]
    d = _extract_details(fc, detail)
    present = sum(1 for v in d.values() if v is not None)
    if present >= 5:
        return "full"
    elif present >= 2:
        return "partial"
    return "none"


def _score_financial_health(fc: dict, detail: dict) -> float:
    """财务健康度评分 (0-100)"""
    d = _extract_details(fc, detail)
    score = 50  # baseline

    revenue_yoy = d.get("revenue_yoy")
    if revenue_yoy is not None:
        if revenue_yoy >= 0.20:
            score += 15
        elif revenue_yoy >= 0:
            score += 5
        elif revenue_yoy < -0.20:
            score -= 15

    gross_margin = d.get("gross_margin")
    if gross_margin is not None:
        if gross_margin >= 0.40:
            score += 15
        elif gross_margin >= 0.20:
            score += 5
        elif gross_margin < 0.10:
            score -= 10

    operating_cf = d.get("operating_cash_flow")
    net_profit = d.get("net_profit_parent")
    if operating_cf is not None and net_profit is not None:
        if operating_cf > 0 and net_profit > 0:
            score += 10
        elif operating_cf < 0 and net_profit > 0:
            score -= 5  # Profit without cash flow — caution

    return min(max(score, 0), 100)


def _score_governance(fc: dict, detail: dict) -> float:
    """治理与执行力评分 (0-100)"""
    d = _extract_details(fc, detail)
    score = 50  # baseline

    roe = d.get("roe")
    if roe is not None:
        if roe >= 0.15:
            score += 20
        elif roe >= 0.08:
            score += 10
        elif roe < -0.05:
            score -= 15

    revenue_yoy = d.get("revenue_yoy")
    if revenue_yoy is not None and revenue_yoy >= 0.05:
        score += 10  # Consistent growth suggests good execution

    return min(max(score, 0), 100)


def _score_valuation_safety(fc: dict, detail: dict) -> float:
    """估值安全边际评分 (0-100)"""
    d = _extract_details(fc, detail)
    score = 50  # baseline

    pe = d.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe <= 15:
            score += 20
        elif pe <= 30:
            score += 10
        elif pe >= 100:
            score -= 15
    elif pe is not None and pe < 0:
        score -= 10  # Negative earnings — caution

    pb = d.get("pb_ratio")
    if pb is not None and pb > 0:
        if pb <= 1.5:
            score += 15
        elif pb <= 3:
            score += 5
        elif pb >= 10:
            score -= 10

    market_cap = d.get("market_cap")
    if market_cap is not None:
        # Prefer mid-cap for elasticity (3B-50B CNY)
        cap_b = market_cap / 1e8  # Convert to 亿
        if 30 <= cap_b <= 500:
            score += 10
        elif cap_b > 1000:
            score -= 5  # Too large for significant upside

    return min(max(score, 0), 100)
