"""
分析报告生成器

根据 ScreeningResult 数据生成标准化 Markdown 分析报告。
报告结构详见 contracts/report-schema.md。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import ScreeningResult

# 事件类型中文映射
EVENT_TYPE_CN = {
    "M_A": "并购重组",
    "CAP_EXPAND": "产能扩张",
    "BIZ_CHANGE": "业务变更/跨界",
    "TECH_COOP": "技术合作",
    "ORDER": "订单落地",
    "OTHER": "其他事件",
    "UNKNOWN": "无法识别",
}

PRIORITY_LABEL = {
    "P0": "最高",
    "P1": "高",
    "P2": "中",
    "NONE": "无",
}

RATING_CN = {
    "A": "A（强烈关注）",
    "B": "B（重点关注）",
    "C": "C（一般关注）",
    "D": "D（维持观察）",
}


def generate_report(result: ScreeningResult) -> str:
    """生成完整 Markdown 分析报告"""
    event_cn = EVENT_TYPE_CN.get(result.event_type, result.event_type)
    pri_cn = PRIORITY_LABEL.get(result.signal_priority, result.signal_priority)
    rating_cn = RATING_CN.get(result.rating_level, result.rating_level)

    # Ratings
    fd = result.fundamental_detail
    idet = result.industry_detail

    # Fundamental metrics
    fdetails = fd.get("details", {}) if fd else {}
    revenue_yoy = fdetails.get("revenue_yoy", "N/A")
    gross_margin = fdetails.get("gross_margin", "N/A")
    roe = fdetails.get("roe", "N/A")
    debt_ratio = fdetails.get("debt_ratio", "N/A")
    rnd_ratio = fdetails.get("rnd_ratio", "N/A")
    net_profit_yoy = fdetails.get("net_profit_yoy", "N/A")

    def _fmt(v, suffix=""):
        if isinstance(v, (int, float)):
            if suffix == "%":
                return f"{v * 100:.1f}%"
            return f"{v:.1f}{suffix}"
        return str(v)

    def _assess(v, high, low, high_good=True):
        if not isinstance(v, (int, float)):
            return "数据不足"
        if high_good:
            if v >= high:
                return "优秀 ✓"
            elif v >= low:
                return "一般"
            else:
                return "较差 ✗"
        else:
            if v <= high:
                return "优秀 ✓"
            elif v <= low:
                return "一般"
            else:
                return "较差 ✗"

    # Industry detail
    idetail = idet.get("details", {}) if idet else {}
    sector_name = idetail.get("sector_name", "待定")

    # Pseudo signals
    pseudo_lines = []
    for ps in (result.pseudo_signals or []):
        severity = ps.get("severity", "low")
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
        pseudo_lines.append(f"- {icon} **{ps.get('type', 'unknown')}**: {ps.get('reason', '')}")

    # Risk assessment
    risk_items = []
    if result.fundamental_score < 40:
        risk_items.append("- ⚠️ 基本面评分较低，需关注财务健康度")
    if result.industry_score < 40:
        risk_items.append("- ⚠️ 产业价值评估分较低，赛道前景有限")
    if result.pseudo_signals:
        high_ps = sum(1 for p in result.pseudo_signals if p.get("severity") == "high")
        if high_ps > 0:
            risk_items.append("- 🔴 存在高优先级伪转型信号，需审慎评估转型真实性")
    if not risk_items:
        risk_items.append("- 未发现显著风险信号")

    lines = [
        f"# 潜力标的分析报告: {result.stock_name}({result.stock_code})",
        "",
        "## 📋 基础信息",
        f"- **股票名称**: {result.stock_name} ({result.stock_code})",
        f"- **触发事件**: {result.announcement_title}",
        f"- **事件类型**: {event_cn}  优先级: {pri_cn}",
        f"- **综合评级**: {rating_cn} (评分: {result.composite_rating}/100)",
        f"- **分析日期**: {result.created_at[:10]}",
        "",
        "---",
        "",
        "## 🚀 触发事件概述",
        f"标的 {result.stock_name}({result.stock_code}) 发布{event_cn}相关公告：\"{result.announcement_title}\"。",
        "",
        "---",
        "",
        "## 🏢 公司基本面",
        "",
        "### 核心财务指标",
        "| 指标 | 数值 | 评估 |",
        "|------|------|------|",
        f"| 营收同比增速 | {_fmt(revenue_yoy, '%')} | {_assess(revenue_yoy, 0.2, -0.1)} |",
        f"| 净利润同比 | {_fmt(net_profit_yoy, '%')} | {_assess(net_profit_yoy, 0.15, -0.2)} |",
        f"| 毛利率 | {_fmt(gross_margin, '%')} | {_assess(gross_margin, 0.30, 0.15)} |",
        f"| ROE | {_fmt(roe, '%')} | {_assess(roe, 0.12, 0.05)} |",
        f"| 资产负债率 | {_fmt(debt_ratio, '%')} | {_assess(debt_ratio, 0.4, 0.6, False)} |",
        f"| 研发费用率 | {_fmt(rnd_ratio, '%')} | {_assess(rnd_ratio, 0.05, 0.02)} |",
        "",
        f"### 基本面评分: {result.fundamental_score}/100",
        f"财务健康度: {fd.get('financial_health', 'N/A')}/100 | "
        f"治理与执行力: {fd.get('governance', 'N/A')}/100 | "
        f"估值安全边际: {fd.get('valuation_safety', 'N/A')}/100",
        "",
        "---",
        "",
        "## 🔬 新赛道产业分析",
        f"### 赛道: {sector_name}",
        "",
        "### 评分明细",
        "| 维度 | 评分 | 权重 |",
        "|------|------|------|",
        f"| 赛道空间 | {idet.get('sector_space', 'N/A')}/100 | 30% |",
        f"| 业务协同性 | {idet.get('biz_synergy', 'N/A')}/100 | 25% |",
        f"| 行业格局影响 | {idet.get('industry_impact', 'N/A')}/100 | 20% |",
        f"| 业绩弹性 | {idet.get('earnings_elasticity', 'N/A')}/100 | 25% |",
        "",
        f"### 综合产业评分: {result.industry_score}/100",
        "",
        "---",
        "",
        "## 💰 增量价值分析",
        f"**综合评级**: {rating_cn}",
        "",
        f"本标的的综合评分为 {result.composite_rating}/100，属于 {rating_cn} 级别。",
        "",
        "---",
        "",
        "## ⚠️ 风险提示",
    ] + risk_items + [
        "",
        "---",
        "",
        "## 🔮 未来展望",
        f"{result.stock_name} 通过{event_cn}切入{sector_name}赛道。"
        f"当前基本面评分 {result.fundamental_score}/100，"
        f"产业价值评估 {result.industry_score}/100，"
        f"综合评级 {rating_cn}。",
        "",
        "建议持续关注转型进展，重点关注公告中提及的业务落地情况和后续财务数据验证。",
    ]

    if pseudo_lines:
        lines = lines[:-5] + [
            "",
            "### 伪转型信号",
        ] + pseudo_lines + [
            "",
            "---",
            "",
        ] + lines[-5:]

    return "\n".join(lines)
