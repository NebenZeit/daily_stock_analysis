# Implementation Plan: 潜力标的智能挖掘系统 (Potential Stock Mining)

**Branch**: `001-potential-stock-mining` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-potential-stock-mining/spec.md`

## Summary

在现有 DSA 框架内新增「潜力标的智能挖掘」子系统，以 A 股公告事件为触发、基本面为底盘、产业增量为核心判断标准，自动化筛选潜在投资标的。系统提供定时自动扫描（盘后）和手动触发（CLI/Web）两种入口，输出结构化分析报告，并支持标的池跟踪管理。

技术方案：新增 cninfo 公告数据获取器（融入现有 data_provider fallback 链），构建公告信号识别 → 基本面过滤 → 产业价值评分的三阶段流水线，采用 JSON 文件化存储（详见 data-model.md），在 main.py 新增 `--potential-stock-mining` CLI 参数，在 Web 前端新增「潜力标的挖掘」页面。

## Technical Context

**Language/Version**: Python 3.10+ (与项目一致)

**Primary Dependencies**:
- 现有 DSA 依赖（litellm, sqlalchemy, pandas, akshare 等）
- 新增：`requests` (cninfo API HTTP 调用，已有间接依赖)
- 新增（可选）：`PyMuPDF` 或 `pdfplumber` (公告 PDF 附件解析，若需全文解析)
- 新增（可选）：`jieba` (中文分词，用于信号关键词匹配)
- cninfo 公告 API：`http://www.cninfo.com.cn/new/hisAnnouncement/query` (POST, form-encoded)
- 已有 `search_service.py` 中的 cninfo 搜索能力可复用

**Storage**: JSON 文件存储（无数据库依赖）。目录结构：
- `data/potential_stock_mining/tasks/` — 扫描任务记录
- `data/potential_stock_mining/results/` — 按月组织的筛选结果
- `data/potential_stock_mining/targets.json` — 跟踪标的清单
- `config/signal_keywords.yaml` — 信号关键词配置
- `config/industry_kb.yaml` — 产业知识库
- `config/screening_rules.yaml` — 筛选规则配置
- 存储引擎：`src/potential_stock_mining/file_store.py`（`MiningFileStore` 类）

**Testing**: pytest (现有)。新增：
- 单元测试：公告信号识别、基本面评分、产业价值评分
- 集成测试：cninfo API 数据获取（mock 化）
- 端到端测试：CLI `--potential-stock-mining` 命令

**Target Platform**: Linux server (GitHub Actions 定时任务) + Windows/macOS (本地开发)

**Project Type**: CLI + Web 功能扩展（在现有 DSA 框架上新增功能模块）

**Performance Goals**:
- 全市场公告扫描 ≤ 2 小时（~5000 只标的，日均公告 50-200 条）
- 增量公告识别 ≤ 15 分钟（从发布到完成筛选）
- 手动触发响应时间 ≤ 5 秒

**Constraints**:
- 不得破坏现有大盘分析、个股分析、通知推送等功能的正常运行
- 单一模块失败不影响其他模块（遵循现有隔离模式）
- 所有配置必须通过 `src/config.py` 的 `Config` dataclass 流入
- 数据源不可用时不得阻塞分析管线
- 公告数据源需有 fallback 机制

**Scale/Scope**: 全市场 A 股（~5000 只），日均增量公告 50-200 条，历史公告回溯可至数年。筛选结果存量预计每月 50-200 条有效标的。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate I: Stability-First Development — PASS
- 新功能以独立模块形式添加，不修改现有分析器的核心逻辑
- 对 main.py 的改动仅限于新增 CLI 参数和条件调用
- Config 类仅新增与潜力挖掘相关的配置项，不改变现有字段语义
- 推荐：将挖掘逻辑封装在 `src/potential_stock_mining/` 独立目录

### Gate II: Contract & Compatibility Preservation — PASS (with notes)
- 需要验证的兼容性点：
  - `main.py` 新增 `--potential-stock-mining` 参数不与现有参数冲突
  - Web 前端新增路由 `/potential-stock-mining` 不与现有路由冲突
  - JSON 文件存储路径不与现有数据目录冲突
  - 筛选结果报告格式不破坏现有通知管道
- 注意：筛选结果通知为可选配置，默认不推送

### Gate III: Multi-Source Data Resilience — PASS (with notes)
- 公告数据源需设计 fallback 链：
  - P0: cninfo API（主数据源）
  - P1: akshare 的 `stock_notice_report` 或类似接口
  - P2: 上交所/深交所官网公告页面解析
- 所有数据源失败时：记录错误、触发告警、返回空结果
- 遵循现有 `BaseFetcher` 模式的错误处理和日志规范

### Gate IV: Documentation-Driven Change — PASS (with notes)
- 必须更新：
  - `.env.example` — 新增公告数据源相关配置项
  - `docs/` — 新增潜力标的挖掘功能使用说明
  - `AGENTS.md` / `CLAUDE.md` — 如有 AI 协作规则变更
- 新增数据库表需生成对应文档

### Gate V: Minimal Surface Change + Validated Delivery — PASS
- 功能是新增独立模块，不涉及现有系统重构
- 仅在必要接触点（main.py CLI, Web 路由, Config 类）扩展
- 每个交付物需附带验证状态和回滚方式

**Gate Verdict**: 所有门禁 PASS。Phase 1 完成后重新检视。

## Project Structure

### Documentation (this feature)

```text
specs/001-potential-stock-mining/
├── spec.md              # Feature specification (已就绪)
├── plan.md              # 本文件 (/speckit-plan 输出)
├── research.md          # Phase 0 输出 — 技术调研与未知项解析
├── data-model.md        # Phase 1 输出 — 数据模型设计
├── quickstart.md        # Phase 1 输出 — 快速验证指南
├── contracts/           # Phase 1 输出 — 接口契约
│   ├── cli-contract.md       # CLI 参数契约
│   ├── api-contract.md       # API 端点契约（Web 后端）
│   └── report-schema.md      # 筛选结果报告 Schema
└── tasks.md             # Phase 2 输出 — 任务清单 (/speckit-tasks 创建)
```

### Source Code (repository root)

```text
src/
├── config.py                    # [+新增配置项] 公告数据源、信号规则、评分阈值
├── potential_stock_mining/      # [新增] 潜力标的挖掘模块
│   ├── __init__.py
│   ├── models.py                    # 数据实体 dataclass 定义
│   ├── file_store.py                # JSON 文件化存储引擎（代替数据库）
│   ├── announcement_fetcher.py      # 公告数据获取（cninfo + fallback）
│   ├── signal_identifier.py         # 信号识别与事件分类
│   ├── fundamental_filter.py        # 基本面质量过滤
│   ├── industry_scorer.py           # 产业增量价值评估
│   ├── pseudo_transformation.py     # 伪转型甄别规则
│   ├── screening_orchestrator.py    # 三阶段流水线编排器
│   ├── report_generator.py          # 分析报告生成
│   ├── industry_knowledge_base.py   # 产业知识库管理
│   └── rule_engine.py               # 筛选规则引擎
├── schemas/                    # [+新增] 数据 Schema
│   └── mining_schemas.py           # 挖掘模块 Pydantic schemas
├── api/                        # [+新增 Web API 端点]
│   └── v1/
│       ├── __init__.py
│       └── potential_stock.py      # 潜力标的 REST API
└── core/
    └── trading_calendar.py     # [利用现有] 交易日历判断

apps/dsa-web/src/
├── api/                        # [+新增] Web API 客户端
│   └── potentialStock.ts
├── pages/                      # [+新增] 页面组件
│   └── PotentialStockMiningPage.tsx
├── components/                 # [+新增] 子组件
│   └── potential-stock-mining/
│       ├── MiningTriggerCard.tsx       # 手动触发卡片
│       ├── MiningResultTable.tsx       # 结果表格
│       ├── TargetDetailModal.tsx       # 标的详情弹窗
│       └── IndustryKbEditor.tsx        # 产业知识库编辑
├── App.tsx                     # [修改] 新增路由
└── Shell.tsx                   # [修改] 导航栏新增入口

main.py                         # [修改] 新增 CLI 参数
```

**Structure Decision**: 选用单一 Python 后端 + React 前端的扁平扩展结构。挖掘逻辑封装在独立 `src/potential_stock_mining/` 包内，与现有代码隔离。数据采用 JSON 文件化存储（`MiningFileStore`），配置、通知等基础设施复用现有层。

## Complexity Tracking

> *Constitution Check 已全部 PASS，无需复杂性违规说明。*
