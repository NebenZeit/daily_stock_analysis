# 筛选结果报告 Schema

> 定义系统自动生成的潜力标的分析报告的标准化结构。

---

## 报告结构

筛选结果报告以 Markdown 格式输出，包含以下章节：

```markdown
# 潜力标的分析报告: {stock_name}({stock_code})

## 📋 基础信息
- **股票名称**: {stock_name} ({stock_code})
- **触发事件**: {event_title}
- **事件类型**: {event_type_label} 优先级: {signal_priority}
- **公告日期**: {publish_date}
- **综合评级**: {rating_level} (评分: {composite_rating}/100)
- **分析日期**: {analysis_date}

---

## 🚀 触发事件概述
{event_description}

---

## 🏢 公司基本面
### 核心财务指标
| 指标 | 数值 | 评估 |
|------|------|------|
| 营收同比增速 | {revenue_yoy}% | {revenue_assessment} |
| 净利润同比 | {net_profit_yoy}% | {profit_assessment} |
| 毛利率 | {gross_margin}% | {margin_assessment} |
| ROE | {roe}% | {roe_assessment} |
| 资产负债率 | {debt_ratio}% | {debt_assessment} |
| 研发费用率 | {rnd_ratio}% | {rnd_assessment} |

### 基本面评分: {fundamental_score}/100
{fundamental_summary}

---

## 📜 事件方案细节
{event_detail}

---

## 🔬 新赛道产业分析
### 赛道: {sector_name}
{sector_analysis}

### 业务协同性分析
{synergy_analysis}

### 产业空间评估
{sector_space_analysis}

---

## 💰 增量价值分析
### 评分明细
| 维度 | 评分 | 说明 |
|------|------|------|
| 赛道空间 | {sector_space_score} | ... |
| 业务协同性 | {biz_synergy_score} | ... |
| 行业格局影响 | {industry_impact_score} | ... |
| 业绩弹性 | {earnings_elasticity_score} | ... |

### 综合产业评分: {industry_score}/100

---

## ⚠️ 风险提示
{risk_disclaimers}

---

## 🔮 未来展望
{outlook}
```

---

## 字段说明

### 基础信息字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `stock_name` | string | 数据源 | 股票名称 |
| `stock_code` | string | 数据源 | 股票代码 |
| `event_title` | string | 公告 | 触发公告标题 |
| `event_type_label` | string | 信号识别 | 中文事件类型 |
| `signal_priority` | string | 信号识别 | P0/P1/P2 |
| `publish_date` | string | 公告 | 公告发布日期 |
| `rating_level` | string | 评分引擎 | A/B/C/D |
| `composite_rating` | float | 评分引擎 | 0-100 |
| `analysis_date` | string | 系统 | 分析执行日期 |

### 评分维度字段

| 字段 | 范围 | 权重 | 说明 |
|------|------|------|------|
| `fundamental_score` | 0-100 | 综合评级输入 | 基本面过滤评分 |
| `industry_score` | 0-100 | 综合评级输入 | 产业价值评分 |
| `composite_rating` | 0-100 | 最终 | `fundamental × 0.5 + industry × 0.5` |
| `sector_space_score` | 0-100 | 25% of industry | 赛道空间 |
| `biz_synergy_score` | 0-100 | 25% of industry | 业务协同性 |
| `industry_impact_score` | 0-100 | 25% of industry | 行业格局影响 |
| `earnings_elasticity_score` | 0-100 | 25% of industry | 业绩弹性 |

---

## 查看方式

```bash
# CLI 终端输出（可通过 shell 重定向保存到文件）
python main.py --potential-stock-mining

# 通过 API 获取完整报告
curl http://localhost:8000/api/v1/potential-stock/results/{id} | jq '.report_md'

# 直接查看文件存储中的原始 JSON
cat data/potential_stock_mining/results/2026/06/{result_id}.json | jq '.report_md'
```

---

## 存储方式

- `report_md` 字段作为 JSON 的一部分存储在结果文件中（`results/YYYY/MM/{result_id}.json`）
- `fundamental_detail` 和 `industry_detail` 以嵌套 JSON 存储在相同文件中
- 历史报告可通过 API `GET /results/{id}` 或直接读取文件获取
