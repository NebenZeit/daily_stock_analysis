# Research: 潜力标的智能挖掘系统 — 技术调研

> Phase 0 output. Resolves all NEEDS CLARIFICATION items from plan.md.

## 1. 公告数据源 — cninfo API

### Decision
选择 cninfo.com.cn 公共 API 作为主数据源（公告查询），akshare/交易所官网作为备用降级。

### Rationale
- cninfo（巨潮资讯网）是证监会指定的上市公司信息披露平台，数据最全、最权威
- 公开 API 无需 Token/认证（需要 SID cookie，可通过 requests.Session 自动管理）
- 已有 Node.js 原型验证了 API 可用性
- 公告 PDF 附件托管在 `https://static.cninfo.com.cn/`，可直接下载

### API 详情
- **Endpoint**: `POST http://www.cninfo.com.cn/new/hisAnnouncement/query`
- **Content-Type**: `application/x-www-form-urlencoded`
- **关键参数**:
  - `stock`: `{stockCode},{orgId}` (orgId 需要映射)
  - `pageNum`/`pageSize`: 分页
  - `seDate`: 日期范围 `YYYY-MM-DD~YYYY-MM-DD`
  - `column`: `szse` (沪深两市), `plate`: `sh`/`sz`/`bj`
- **响应**: `{ announcements: [{ announcementTitle, announcementTime, adjunctUrl }], totalAnnouncement }`
- **Session 管理**: 使用 `requests.Session()` 自动获取和维持 SID cookie

### orgId 映射方案
**决策**: 构建本地 orgId 映射表（JSON/DB），一次性批量获取全部 A 股 ~5000 只代码的 orgId。

**方案**:
1. 利用 cninfo 的公开搜索/股票页面来解析 orgId（从 Referer URL 模式提取）
2. 或者通过 akshare `stock_info_a_code_name()` 获取基础股票列表，再拼接 cninfo URL 逐个获取 orgId
3. 首次运行时自动构建映射表，后续从本地缓存读取
4. **首次部署回扫范围**: 回扫近 30 天公告作为初始数据池。不进行全量历史回溯。

**降级方案**:
- P0: cninfo API（通过 orgId 映射）
- P1: akshare `stock_notice_report` 接口（若有）
- P2: 直接通过搜索引擎搜索 "股票代码 公告"（利用现有 SearchService）

### Alternatives Considered
- **使用现有搜索服务**: 现有 `search_service.py` 已经有公告搜索能力（通过搜索引擎），但这是间接搜索，无法精确控制时间范围和事件类型，且没有结构化响应
- **使用 akshare 公告接口**: akshare 有 `stock_notice_report` 等接口，但数据来源同样是 cninfo，数据质量受 akshare 维护状态影响，且缺少 orgId 级别的精确查询

---

## 2. 信号识别与事件分类

### Decision
基于公告标题关键词匹配 + LLM 辅助分类的两阶段策略。

### Rationale
- 第一阶段：标题关键词/正则匹配，快速分类为已知事件类型（并购、产能扩张等）
- 第二阶段：对无法明确分类的公告，调用 LLM 进行语义理解分类
- 关键词库以 YAML 配置文件形式维护（`config/signal_keywords.yaml`）

### 事件类型与关键词

| 事件类型 | 优先级 | 示例关键词 |
|---------|--------|-----------|
| 并购重组 | P0 | 收购、并购、重组、重大资产重组、借壳、吸收合并 |
| 产能扩张 | P0 | 投资建设、扩产、新建项目、产能扩建、生产基地 |
| 业务变更 | P1 | 变更经营范围、新增业务、跨界、转型、进军 |
| 技术合作 | P1 | 战略合作、签订协议、联合研发、技术许可 |
| 订单落地 | P2 | 重大合同、中标、订单、框架协议、供货合同 |

### 伪转型甄别规则
结合关键词 + 基本面数据判断：
- 新赛道与主业完全无关（跨行业代码差异大）→ 降权
- 公告日期在行情火热期（板块涨幅 > 30%）→ 标记关注
- 落地形式为框架协议/意向书而无实质进展 → 降权
- 研发费用率 < 3% 且无核心技术专利 → 降权

### Alternatives Considered
- **纯 LLM 分类**: 灵活但成本高、延迟大、不适合批量处理
- **纯规则匹配**: 速度快但召回率有限，难以处理长尾事件

---

## 3. 基本面过滤 — 复用现有基础设施

### Decision
- 复用现有的 `DataFetcherManager.get_fundamental_context()` 获取基础财务数据
- 额外通过 akshare 补充资产负债表指标（资产负债率、流动比率等）
- 评分规则以配置文件形式管理

### Rationale
现有基本面管道提供 7 个数据块（估值、成长、盈利、机构、资金流、龙虎榜、板块），覆盖了基本面过滤的 80% 需求。缺失的指标（资产负债率、自由现金流等）需从 akshare 额外获取。

### 可用指标映射

| 过滤维度 | 可用来源 | 状态 |
|---------|---------|------|
| 营收/利润同比 | `growth.revenue_yoy`, `growth.net_profit_yoy` | ✅ 已有 |
| 毛利率 | `growth.gross_margin` | ✅ 已有 |
| ROE | `growth.roe` | ✅ 已有 |
| PE/PB/市值 | `valuation.*` | ✅ 已有 |
| 现金流 | `earnings.financial_report.operating_cash_flow` | ✅ 已有 |
| 资产负债率 | 需通过 akshare `stock_financial_abstract` 补充 | ❌ 新增 |
| 研发费用率 | 需从财报明细获取 | ❌ 新增 |
| 实控人/管理层 | 需从 akshare `stock_management_info` 获取 | ❌ 新增 |

### Alternatives Considered
- **引入新数据源**: 如 Tushare Pro（需 Token）或 Wind（收费）— 过度依赖外部付费接口
- **使用 LLM 直接从公告文本提取财务指标**: 准确率不可控，不适合批量处理

---

## 4. 产业价值评分

### Decision
基于评分规则的轻量化评分引擎 + LLM 辅助评估的综合方案。

### Rationale
- 规则引擎覆盖可量化的指标（赛道空间、业绩弹性、协同性等）
- LLM 辅助覆盖需要主观判断的维度（行业格局影响、技术路线前景）
- 最终综合评级 = 规则评分 × 0.7 + LLM 评分 × 0.3

### 评分维度与权重

| 维度 | 权重 | 数据来源 | 评估方式 |
|------|------|---------|---------|
| 赛道空间 | 30% | 产业知识库 + 行业数据 | 市场规模、增速、渗透率 |
| 业务协同性 | 25% | 基本面数据 + 公告内容 | 与主业关联度、技术共享度 |
| 行业格局影响 | 20% | LLM 分析 | 竞争格局变化、先发优势 |
| 业绩弹性 | 25% | 财务数据 | 营收占比、利润率影响 |

---

## 5. 产业知识库初版设计

### Decision
YAML 配置文件形式维护，初始预设三个赛道。

### 默认赛道

```yaml
ai_computing_upstream:  # AI 算力上游
  name: "AI 算力上游材料"
  keywords: [算力, GPU, AI芯片, HBM, 光模块, 服务器, 液冷, PCB, 存储]
  related_industries: [电子, 计算机, 通信]
  products: [AI服务器, 高速光模块, HBM内存, AI芯片]
  
ai_healthcare:  # AI+医疗
  name: "AI+医疗"
  keywords: [AI诊断, 医学影像, 智慧医疗, 医疗AI, 基因测序]
  related_industries: [医药生物, 计算机]
  products: [AI辅助诊断系统, 智能影像分析]
  
ai_drug_discovery:  # AI+药物研发
  name: "AI+药物研发"
  keywords: [AI制药, 药物研发, 分子筛选, 临床试验AI, 计算机辅助药物设计]
  related_industries: [医药生物, 计算机, 基础化工]
  products: [AI药物发现平台, 分子模拟软件]
```

---

## 6. PDF 解析策略

### Decision
第一阶段仅基于公告标题进行分类，暂不深入解析 PDF 附件正文。

### Rationale
- 标题信息足够覆盖 80%+ 的事件分类需求（公告标题通常包含事件类型词）
- PDF 解析复杂度高（扫描件 OCR、格式多样），可后续迭代
- 在 edge case 中保留"解析失败"标记机制

### 后续迭代
- 如需深度提取公告细节（如交易金额、交易对手等），可使用 PyMuPDF/pdfplumber
- 对于扫描件 PDF，需引入 OCR 引擎（PaddleOCR/Tesseract）

---

## 7. Web 前端集成

### Decision
在现有 React 前端的导航栏新增「潜力标的」入口，新增独立页面。

### Rationale
已有成熟的 UI 模式可复用：
- 路由添加: `App.tsx` 新增 `<Route>`（lazy load 模式）
- 导航: `SidebarNav.tsx` 的 `NAV_ITEMS` 数组加一项
- API 客户端: `src/api/potentialStock.ts` 遵循 `alphasift.ts` 模式
- 后端 API: `api/v1/endpoints/potential_stock.py` 遵循 `alphasift.py` 模式

### 页面结构
- 首页: 手动触发按钮 + 历史筛选结果列表（表格形式）
- 详情弹窗: 展示单条筛选结果完整报告
- 知识库管理页（P3）: 赛道编辑表单

---

## 8. CLI 集成

### Decision
在 `main.py` 新增 `--potential-stock-mining` 参数，支持 `--since`/`--until` 子参数。

### CLI 接口设计

```bash
# 默认扫描（最近一个交易日）
python main.py --potential-stock-mining

# 指定时间范围
python main.py --potential-stock-mining --since 2026-06-01 --until 2026-06-20

# 指定特定股票（定向扫描）
python main.py --potential-stock-mining --stocks 600519,000001

# 赛道定向（P3）
python main.py --potential-stock-mining --sector ai_computing_upstream
```

### 集成方式
- 在 `parse_arguments()` 中新增 `--potential-stock-mining` 互斥参数组
- `main()` 中新增 `Mode 4`：潜力标的挖掘模式
- 通过 `potential_stock_mining/screening_orchestrator.py` 入口执行

---

## 9. Config 配置项

### Decision
新增配置遵循现有 `src/config.py` 模式，通过 `.env` 加载。

### 新增配置项

```python
# 公告数据源
cninfo_request_timeout: int = 15        # cninfo API 超时（秒）
cninfo_max_retries: int = 3             # 重试次数
cninfo_page_size: int = 50              # 每页公告数

# 定时扫描
potential_stock_schedule_enabled: bool = False    # 是否启用定时扫描
potential_stock_schedule_time: str = "18:00"      # 定时扫描时间
potential_stock_incremental_interval: int = 15    # 增量轮询间隔（分钟）

# 通知
potential_stock_notify_enabled: bool = False      # 是否推送筛选结果
```

---

## 10. 数据库设计 — 新增实体

| 表名 | 主键 | 关键字段 |
|------|------|---------|
| `announcements` | `id` (UUID) | `stock_code`, `title`, `publish_time`, `event_type`, `adjunct_url`, `status` |
| `screening_results` | `id` (UUID) | `stock_code`, `event_type`, `signal_priority`, `fundamental_score`, `industry_score`, `composite_rating`, `report_md`, `scan_task_id` |
| `tracked_targets` | `id` (UUID) | `stock_code`, `status` (观察/跟踪/剔除), `added_at`, `removed_reason` |
| `industry_knowledge_base` | `id` (UUID) | `sector_name`, `keywords`, `products`, `related_industries`, `updated_at` |
| `screening_rules` | `id` (UUID) | `name`, `type` (event/fundamental/exclusion), `params` (JSON), `enabled` |
| `scan_tasks` | `id` (UUID) | `trigger_type` (scheduled/manual), `status`, `started_at`, `completed_at`, `scan_range`, `error_log` |

---

## 11. 未被采用的技术依赖

| 技术 | 原因 |
|------|------|
| Celery/RabbitMQ | 当前项目无分布式任务队列需求，`task_queue.py` 的内置线程池足够 |
| Redis | 缓存需求可由现有 LRU 缓存和数据库满足 |
| Scrapy | 公告爬取仅限单个 API endpoint，不需要完整的爬虫框架 |
| PaddleOCR/Tesseract | 第一阶段不解析 PDF 正文，后续迭代时评估 |
| Tushare Pro | 需要付费 Token，且公告数据同样来自 cninfo |
