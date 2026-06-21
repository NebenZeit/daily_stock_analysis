"""
筛选规则引擎
加载 YAML 配置的筛选规则，提供规则匹配和评估功能。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


# Default rules path relative to project root
DEFAULT_RULES_PATH = "config/screening_rules.yaml"


def load_rules(path: Optional[str] = None) -> list[dict]:
    """从 YAML 加载筛选规则"""
    path = path or DEFAULT_RULES_PATH
    p = Path(path)
    if not p.exists():
        logger.warning("Screening rules file not found: %s", p)
        return _default_rules()
    try:
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rules = data.get("rules", []) if isinstance(data, dict) else []
        return [r for r in rules if r.get("enabled", True)]
    except Exception as e:
        logger.error("Failed to load screening rules from %s: %s", path, e)
        return _default_rules()


def _default_rules() -> list[dict]:
    """返回内置默认规则"""
    return [
        {
            "name": "并购重组信号",
            "rule_type": "EVENT",
            "params": {
                "event_type": "M_A",
                "priority": "P0",
                "include_keywords": ["收购", "并购", "重组", "借壳", "吸收合并"],
                "exclude_keywords": ["出售", "转让"],
            },
            "enabled": True,
            "priority": 10,
        },
        {
            "name": "产能扩张信号",
            "rule_type": "EVENT",
            "params": {
                "event_type": "CAP_EXPAND",
                "priority": "P0",
                "include_keywords": ["投资建设", "扩产", "新建项目", "产能扩建", "生产基地"],
                "exclude_keywords": [],
            },
            "enabled": True,
            "priority": 9,
        },
        {
            "name": "基本面最低门槛",
            "rule_type": "FUNDAMENTAL",
            "params": {
                "min_revenue_yoy": -0.3,
                "min_gross_margin": 0.10,
                "min_market_cap": 500_000_000,
            },
            "enabled": True,
            "priority": 5,
        },
        {
            "name": "ST 标的排除",
            "rule_type": "EXCLUSION",
            "params": {"exclude_st": True, "exclude_pt": True},
            "enabled": True,
            "priority": 1,
        },
    ]


def match_rules(rules: list[dict], rule_type: str) -> list[dict]:
    """按类型过滤规则"""
    return [r for r in rules if r.get("rule_type") == rule_type]


def evaluate_fundamental_rules(
    rules: list[dict], fundamental_data: dict
) -> tuple[bool, list[str]]:
    """
    评估基本面规则，返回 (pass, reasons)
    fundamental_data 结构参考 MiningFileStore fundamental_detail
    """
    passed = True
    reasons = []
    fund_rules = match_rules(rules, "FUNDAMENTAL")
    details = fundamental_data.get("details", {})

    for rule in fund_rules:
        params = rule.get("params", {})
        name = rule.get("name", "unknown")

        min_revenue = params.get("min_revenue_yoy")
        if min_revenue is not None:
            val = details.get("revenue_yoy")
            if val is not None and val < min_revenue:
                passed = False
                reasons.append(f"{name}: revenue_yoy {val} < {min_revenue}")

        min_margin = params.get("min_gross_margin")
        if min_margin is not None:
            val = details.get("gross_margin")
            if val is not None and val < min_margin:
                passed = False
                reasons.append(f"{name}: gross_margin {val} < {min_margin}")

        min_cap = params.get("min_market_cap")
        if min_cap is not None:
            val = details.get("market_cap")
            if val is not None and val < min_cap:
                passed = False
                reasons.append(f"{name}: market_cap {val} < {min_cap}")

    return passed, reasons
