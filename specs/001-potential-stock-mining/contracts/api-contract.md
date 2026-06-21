# API 接口契约: 潜力标的挖掘

> 定义 REST API 端点及其请求/响应格式。全部位于 `/api/v1/potential-stock` 命名空间下。

---

## 端点总览

| 方法 | 路径 | 说明 | P1/P2 |
|------|------|------|-------|
| POST | `/api/v1/potential-stock/scan` | 手动触发挖掘扫描 | P1 |
| GET | `/api/v1/potential-stock/results` | 获取筛选结果列表 | P1 |
| GET | `/api/v1/potential-stock/results/{id}` | 获取单个筛选结果详情 | P1 |
| GET | `/api/v1/potential-stock/tasks` | 获取扫描任务历史 | P1 |
| GET | `/api/v1/potential-stock/tasks/{id}` | 获取单个扫描任务详情 | P1 |
| GET | `/api/v1/potential-stock/targets` | 获取跟踪标的列表 | P2 |
| PUT | `/api/v1/potential-stock/targets/{stock_code}/status` | 更新标的跟踪状态 | P2 |
| GET | `/api/v1/potential-stock/targets/{stock_code}` | 获取标的详情（含关联结果） | P2 |
| GET | `/api/v1/potential-stock/sectors` | 获取赛道列表 | P3 |
| GET | `/api/v1/potential-stock/rules` | 获取筛选规则 | P3 |

---

## POST /api/v1/potential-stock/scan

手动触发潜力标的挖掘扫描。

### Request Body

```json
{
  "since": "2026-06-01",
  "until": "2026-06-20",
  "target_stocks": ["600519", "000001"],
  "sector": "ai_computing_upstream"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `since` | string(date) | 否 | 最近交易日 | 扫描起始日期 |
| `until` | string(date) | 否 | 最近交易日 | 扫描截止日期 |
| `target_stocks` | string[] | 否 | [] (全市场) | 指定标的列表 |
| `sector` | string | 否 | null | 赛道过滤 |

### Response (200)

```json
{
  "task_id": "a1b2c3d4-...",
  "status": "PENDING",
  "message": "Scan task submitted. Use GET /tasks/{id} to track progress."
}
```

### Response (409 — 已有任务执行中)

```json
{
  "detail": "已有扫描任务正在执行中，请等待完成后再试",
  "active_task_id": "e5f6g7h8-..."
}
```

---

## GET /api/v1/potential-stock/results

获取筛选结果列表，支持分页和筛选。

### Query Parameters

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `page` | int | 否 | 1 | 页码 |
| `page_size` | int | 否 | 20 | 每页条数 |
| `event_type` | string | 否 | 全部 | 事件类型过滤 |
| `rating_level` | string | 否 | 全部 | 评级等级过滤 |
| `since` | string(date) | 否 | -30天 | 起始日期 |
| `until` | string(date) | 否 | 今天 | 截止日期 |
| `stock_code` | string | 否 | 全部 | 指定标的 |
| `sort_by` | string | 否 | `created_at` | 排序字段 |
| `sort_order` | string | 否 | `desc` | 排序方向 |

### Response (200)

```json
{
  "items": [
    {
      "id": "uuid",
      "stock_code": "600519",
      "stock_name": "贵州茅台",
      "event_type": "M_A",
      "signal_priority": "P0",
      "announcement_title": "收购XX公司股权公告",
      "fundamental_score": 85.0,
      "industry_score": 75.0,
      "composite_rating": 82.0,
      "rating_level": "A",
      "created_at": "2026-06-20T14:30:00",
      "tracked_status": "OBSERVING"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

## GET /api/v1/potential-stock/results/{id}

获取单个筛选结果的完整报告。

### Response (200)

```json
{
  "id": "uuid",
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "event_type": "M_A",
  "signal_priority": "P0",
  "announcement_title": "收购XX公司股权公告",
  "fundamental_score": 85.0,
  "fundamental_detail": {
    "financial_health": 85,
    "governance": 70,
    "valuation_safety": 60
  },
  "industry_score": 75.0,
  "industry_detail": {
    "sector_space": 75,
    "biz_synergy": 60,
    "industry_impact": 55,
    "earnings_elasticity": 70
  },
  "composite_rating": 82.0,
  "rating_level": "A",
  "pseudo_signals": [],
  "report_md": "# 潜力标的分析报告\n\n...全文Markdown...",
  "created_at": "2026-06-20T14:30:00",
  "task_id": "scan-task-uuid",
  "announcement": {
    "id": "announcement-uuid",
    "title": "收购XX公司股权公告",
    "publish_time": "2026-06-20T09:00:00",
    "adjunct_url_pdf": "https://static.cninfo.com.cn/..."
  }
}
```

---

## PUT /api/v1/potential-stock/targets/{stock_code}/status

更新标的跟踪状态。

### Request Body

```json
{
  "status": "TRACKING",
  "reason": "基本面稳健，转型可行"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 是 | 目标状态：`OBSERVING` / `TRACKING` / `REMOVED` |
| `reason` | string | 否 | 状态变更原因（REMOVED 时必填） |

### Response (200)

```json
{
  "stock_code": "600519",
  "previous_status": "OBSERVING",
  "current_status": "TRACKING",
  "updated_at": "2026-06-20T15:00:00"
}
```

---

## 错误响应格式

所有端点统一错误格式（复用 DSA 现有模式）：

```json
{
  "detail": "错误描述信息",
  "code": "ERROR_CODE",
  "timestamp": "2026-06-20T14:30:00"
}
```

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 400 | 请求参数错误（如日期格式错误） |
| 404 | 资源不存在 |
| 409 | 冲突（如扫描任务已在执行） |
| 500 | 服务内部错误 |
