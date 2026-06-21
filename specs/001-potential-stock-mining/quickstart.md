# 潜力标的智能挖掘系统 — 快速验证指南

> Phase 1 output. 定义可运行的验证场景，用于确认功能按预期工作。

---

## 前提条件

- DSA 项目本地开发环境已配置（Python 3.10+，依赖已安装）
- `.env` 文件已配置（至少数据库路径）
- 网络可访问 `www.cninfo.com.cn`（A 股公告数据源）
- 可选: 配置 `POTENTIAL_STOCK_SCHEDULE_ENABLED=true` 测试定时模式

---

## 场景 1：CLI 手动触发 — 基本扫描

### 验证目标
确认 CLI `--potential-stock-mining` 命令可正常启动扫描。

### 执行命令
```bash
# 扫描最近一个交易日
python main.py --potential-stock-mining --dry-run

# 扫描指定日期范围（推荐：使用一个已知有公告的日期）
python main.py --potential-stock-mining --since 2026-06-01 --until 2026-06-20 --dry-run
```

### 预期结果
```
===== 潜力标的挖掘结果 =====
📊 扫描范围: 2026-06-01 ~ 2026-06-20
📋 共扫描 N 条公告（dry-run 模式，仅获取数据）
```

- 控制台显示扫描时间范围和公告数量
- `--dry-run` 模式下不执行 AI 分析，仅输出数据获取统计
- 无误报异常（cninfo API 连接超时等应有友好的错误提示）

### 数据模型验证
```bash
# 验证数据库表已创建
python -c "from src.storage import get_db; db = get_db(); print(db.get_table_names())"
```

预期输出包含: `announcements`, `screening_results`, `scan_tasks` 等表名。

---

## 场景 2：CLI 手动触发 — 完整扫描

### 验证目标
确认完整的流水线（公告获取 → 信号识别 → 基本面过滤 → 产业评分）可正常执行。

### 执行命令
```bash
# 对指定股票执行定向扫描
python main.py --potential-stock-mining --since 2026-06-01 --until 2026-06-20 --stocks 600519 --no-notify
```

### 预期结果
```
===== 潜力标的挖掘结果 =====
📊 扫描范围: 2026-06-01 ~ 2026-06-20
📋 共扫描 N 条公告，命中 M 个信号

【P0】并购重组（X条）
  ⭐ 600519 贵州茅台 — 公告标题（评分 Y/100）

【P1】产能扩张（X条）
...

详细报告已保存至数据库。
```

- 输出结构化结果（按优先级分组）
- 每条结果包含股票代码、名称、触发公告、综合评分
- 数据库 `screening_results` 表新增对应记录
- `--no-notify` 模式下不发送推送

---

## 场景 3：验证空结果场景

### 验证目标
确认当日无新增有效信号时，系统输出空报告而非崩溃。

### 执行命令
```bash
# 凌晨等无公告时段，或指定一个极窄时间窗口
python main.py --potential-stock-mining --since 2026-01-01 --until 2026-01-02 --no-notify
```

### 预期结果
```
===== 潜力标的挖掘结果 =====
📊 扫描范围: 2026-01-01 ~ 2026-01-02
📋 共扫描 0 条公告

当日无新增潜力标的。
```

- 无异常堆栈
- 数据库 `scan_tasks` 表中有一条 COMPLETED 记录（结果数为 0）
- 不影响现有分析流程

---

## 场景 4：Web 手动触发（需要 Web 服务）

### 验证目标
确认 Web 前端可正常触发扫描并展示结果。

### 启动 Web 服务
```bash
# 方式 1：通过 main.py
python main.py --serve

# 方式 2：通过 uvicorn
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 操作步骤
1. 打开浏览器访问 `http://localhost:8000`
2. 导航至「潜力标的」页面（侧边栏新增入口）
3. 点击「立即分析」按钮
4. 等待任务完成
5. 查看结果列表

### 预期结果
- 点击后出现任务进度提示
- 完成后结果列表刷新，显示最近筛选结果
- 每行包含: 股票代码、名称、事件类型、评级、评分
- 点击某行可查看完整报告详情

---

## 场景 5：单个标的详情查看

### 验证目标
确认筛选结果详情页面可完整展示分析报告。

### 操作步骤
1. 在结果列表中找到一条结果
2. 点击查看详情
3. 验证报告完整性

### 预期结果
- 详情弹窗/页面展示完整 Markdown 报告
- 包含: 基础信息、事件概述、基本面分析、产业分析、评分明细、风险提示
- 报告排版正确，Markdown 渲染正常
- 字段参考 `contracts/report-schema.md` 确认完整

---

## 场景 6：数据源不可用 — 容错验证

### 验证目标
确认 cninfo 数据源不可用时系统降级行为正常。

### 操作步骤
1. 临时断开网络或修改 hosts 使 `www.cninfo.com.cn` 不可达
2. 执行扫描命令

### 预期结果
```
===== 潜力标的挖掘结果 =====
⚠️ 公告数据源 cninfo 暂时不可用
📋 降级至备选数据源: akshare
...
```
或（全部失败时）:
```
===== 潜力标的挖掘结果 =====
❌ 所有公告数据源均不可用，扫描失败
```

- 记录错误日志
- 不阻塞主流程
- 现有分析功能不受影响

---

## 场景 7：定时任务模式

### 验证目标
确认定时扫描任务可正常启动。

### 操作步骤
1. 在 `.env` 中配置:
   ```ini
   POTENTIAL_STOCK_SCHEDULE_ENABLED=true
   POTENTIAL_STOCK_SCHEDULE_TIME=18:00
   ```
2. 启动定时模式:
   ```bash
   python main.py --schedule
   ```

### 预期结果
```
[定时任务] 潜力标的挖掘已启用，每日 18:00 执行
```

- 到预定时间自动触发扫描
- 扫描结果写入数据库
- 可配置通知推送（可选）

---

## 场景 8：并发请求处理

### 验证目标
确认手动触发与已有任务冲突时拒绝新请求。

### 操作步骤
1. 启动一个扫描任务（可通过长耗时扫描模拟）
2. 扫描进行中时，再次通过 CLI 或 API 触发扫描

### 预期结果（CLI）
```
❌ 已有扫描任务正在执行中（任务 ID: xxx），请等待完成后再试
```
系统拒绝新请求，不排队、不中断已有任务。

### 预期结果（API）
```json
HTTP 409 Conflict
{
  "detail": "已有扫描任务正在执行中，请等待完成后再试"
}
```

### 不通过的场景
- 排队等待当前任务完成后自动执行（不在 Phase 1 范围内）
- 中断当前任务以执行新任务（不支持）

---

## 验证清单

| 编号 | 场景 | P1/P2 | 自动化可测 |
|------|------|-------|-----------|
| V1 | CLI dry-run 扫描 | P1 | ✅ pytest |
| V2 | CLI 完整扫描（指定股票） | P1 | ✅ pytest (mock cninfo) |
| V3 | 空结果场景 | P1 | ✅ pytest (mock 零公告) |
| V4 | Web 手动触发 | P1 | ❌ 需人工（或用 Playwright） |
| V5 | 详情查看 | P1 | ❌ 需人工 |
| V6 | 数据源不可用 | P1 | ✅ pytest (mock 连接失败) |
| V7 | 定时任务 | P1 | ✅ pytest (mock scheduler) |
| V8 | 并发请求处理 | P1 | ✅ pytest (mock running task) |

### 自动化测试规划（参考 `data-model.md`）

```bash
# 运行公告获取单元测试
pytest tests/test_potential_stock_mining/ -m "unit" -v

# 运行集成测试（mock cninfo）
pytest tests/test_potential_stock_mining/ -m "integration" -v

# 运行全流程端到端测试
pytest tests/test_potential_stock_mining/ -m "e2e" -v
```

详情见 `data-model.md` 实体定义和 `contracts/` 接口契约。
