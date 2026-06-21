---

description: "Task list for 潜力标的智能挖掘系统 feature implementation"

---

# Tasks: 潜力标的智能挖掘系统 (Potential Stock Mining)

**Input**: Design documents from `specs/001-potential-stock-mining/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No explicit test tasks requested in spec. Tests are NOT included by default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Core mining module**: `src/potential_stock_mining/`
- **Data files**: `data/potential_stock_mining/`
- **Config files**: `config/`
- **Schemas**: `src/schemas/`
- **API endpoints**: `src/api/v1/`
- **Web frontend**: `apps/dsa-web/src/`
- **Config**: `src/config.py`
- **Main entry**: `main.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — directory structure, config entries, dependency verification

- [X] T001 Create `src/potential_stock_mining/` package directory with `__init__.py`
- [X] T002 Add config entries to `src/config.py` (cninfo API timeout/retry, schedule settings, notification toggle)
- [X] T003 Add config entries to `.env.example` documenting all new `POTENTIAL_STOCK_*` variables
- [X] T004 [P] Add `cninfo.com.cn` to proxy bypass in `src/config.py` (if not already listed)
- [X] T005 Verify `requests` dependency availability (used by cninfo API client)
- [X] T006 Create `tests/test_potential_stock_mining/` test directory with `__init__.py` and `conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core mining pipeline that both US1 and US2 depend on. MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Layer — Dataclass Models & FileStore

- [X] T007 [P] Create dataclass models in `src/potential_stock_mining/models.py` — define `Announcement`, `ScreeningResult`, `ScanTask`, `TrackedTarget` per `data-model.md`
- [X] T008 Create `MiningFileStore` in `src/potential_stock_mining/file_store.py` — JSON file storage engine: result CRUD (`save_result`, `get_result`, `list_results`), task CRUD, target CRUD, index rebuild. See `data-model.md` File Storage Structure section
- [X] T009 Implement file store query methods — `list_results()` with date range, event_type, rating_level, stock_code filters and pagination; `list_tasks()` with limit
- [X] T010 Implement file store tracking methods — `save_target()`, `get_target()`, `update_target_status()` with target state machine enforcement

### Core Mining Pipeline

- [X] T011 Create cninfo announcement API fetcher in `src/potential_stock_mining/announcement_fetcher.py` — implement HTTP client with `requests.Session`, SID cookie management, pagination, orgId resolution mechanism
- [X] T012 Create signal identifier in `src/potential_stock_mining/signal_identifier.py` — implement keyword-based event classification (M&A, capacity expansion, business change, tech cooperation, order fulfillment) with priority mapping
- [X] T013 Create pseudo-transformation detection module in `src/potential_stock_mining/pseudo_transformation.py` — implement rules for detecting fake pivots (unrelated sectors, hype timing, shell companies, low R&D)
- [X] T014 Create fundamental filter in `src/potential_stock_mining/fundamental_filter.py` — implement scoring using existing `DataFetcherManager.get_fundamental_context()`, with thresholds for financial health, governance, and valuation safety
- [X] T015 Create industry value scorer in `src/potential_stock_mining/industry_scorer.py` — implement 4-dimension scoring engine (sector space, biz synergy, industry impact, earnings elasticity) with configurable weights
- [X] T016 Create report generator in `src/potential_stock_mining/report_generator.py` — generate standardized Markdown analysis reports per `contracts/report-schema.md`
- [X] T017 Create screening orchestrator in `src/potential_stock_mining/screening_orchestrator.py` — wire together the 3-stage pipeline (signal identification → fundamental filter → industry scorer → report generation), with `run_scan()` method that accepts date range and optional stock/sector filter
- [X] T018 Create initial signal keyword YAML config in `config/signal_keywords.yaml` with default event type keywords and priority mappings
- [X] T019 Create initial industry knowledge base YAML config in `config/industry_kb.yaml` with 3 default sectors (AI computing upstream, AI+healthcare, AI+drug discovery)
- [X] T020 Create rule engine in `src/potential_stock_mining/rule_engine.py` — load and evaluate screening rules from `config/screening_rules.yaml`

### Pydantic Schemas

- [X] T021 [P] Create mining module Pydantic schemas in `src/schemas/mining_schemas.py` — define `AnnouncementSchema`, `ScreeningResultSchema`, `ScanTaskSchema`, `TrackedTargetSchema` for API serialization

**Checkpoint**: Core mining pipeline + file store ready. User story implementation can now begin.

---

## Phase 3: User Story 1 — 定时自动扫描公告并筛选潜力标的 (Priority: P1) 🎯 MVP

**Goal**: 系统每个交易日盘后自动扫描全市场公告，识别跨界转型、产能扩张、并购整合等事件信号，经过基本面过滤和产业价值评分后，输出当日新增潜力标的清单，数据写入 JSON 文件。

**Independent Test**: 配置一个已知有重大并购公告的交易日，运行定时扫描或单次执行后验证是否输出了对应的潜力标的条目，且 JSON 文件结构与 `data-model.md` 一致。

### Implementation for User Story 1

- [X] T022 [P] [US1] Add `run_potential_stock_mining()` entry function in `src/potential_stock_mining/__init__.py` that initializes orchestrator and file store, then executes scan. Default scan range = last 30 days (first-run backfill); scheduled runs use last trading day
- [X] T023 [P] [US1] Implement scheduled scan integration — added to `main.py` scheduler mode as background task `daily_potential_stock_scan()` with configurable schedule time and incremental interval
- [X] T024 [P] [US1] Implement incremental polling — integrated via `_ps_interval * 60` seconds background task in scheduler
- [X] T025 [US1] Implement scan deduplication — orchestrator uses file store; no duplicate announcements from same cninfo request (per-stock pagination handles dedup naturally)
- [X] T026 [US1] Add empty report handling — orchestrator returns empty results list when no signals; `__init__.py` prints "当日无新增潜力标的"
- [X] T027 [US1] Wire notification — optional push of daily mining brief via existing NotificationService (respects `POTENTIAL_STOCK_NOTIFY_ENABLED`, sends daily digest when enabled)
- [X] T028 [US1] Add error handling for data source failures — graceful fallback in `announcement_fetcher.py` with error_log on scan task

**Checkpoint**: At this point, User Story 1 should be fully functional — scheduled scan runs, outputs results to JSON files, generates reports, handles empty/failure scenarios.

---

## Phase 4: User Story 2 — 手动触发潜力标的挖掘 (Priority: P1)

**Goal**: 用户可以通过 CLI 命令 `python main.py --potential-stock-mining` 或 Web 工作台手动触发扫描，支持 `--since`/`--until` 时间范围参数和 `--stocks` 指定标的。

**Independent Test**: 通过 CLI 运行指定日期范围的扫描命令，验证系统仅扫描该时间段的公告并输出 JSON 结果文件；Web 界面点击"立即分析"按钮后能观察到任务进度和结果展示。

### Implementation for User Story 2 — CLI

- [X] T029 [US2] Add `--potential-stock-mining` CLI argument in `main.py` `parse_arguments()` per `contracts/cli-contract.md`
- [X] T030 [US2] Add `--since` and `--until` CLI arguments in `main.py` for date range control
- [X] T031 [US2] Add `--sector` CLI argument in `main.py` for sector-specific mining (hook for US4)
- [X] T032 [US2] Implement Mode 4 execution in `main()` — call `run_potential_stock_mining()` when `--potential-stock-mining` is set
- [X] T033 [US2] Implement structured console output — grouped by priority, with stock code, name, event type, and composite rating (in `__init__.py`)
- [X] T034 [US2] Handle CLI concurrency guard — checks `MiningFileStore.has_running_task()` before starting, rejects with task ID reference

### Implementation for User Story 2 — Web API

- [X] T035 [US2] Create API endpoint module in `src/api/v1/endpoints/potential_stock.py` — `POST /api/v1/potential-stock/scan` per `contracts/api-contract.md`
- [X] T036 [US2] Register the new router in `src/api/v1/router.py`
- [X] T037 [US2] Implement scan task via existing background task queue (`src/services/task_queue.py`) — async execution with status tracking, results saved via `MiningFileStore`
- [X] T038 [US2] Implement `GET /api/v1/potential-stock/tasks/{id}` for task status polling (read from file store)
- [X] T039 [US2] Implement HTTP 409 conflict response when a scan is already running

### Implementation for User Story 2 — Web Frontend

- [X] T040 [US2] Create API client module in `apps/dsa-web/src/api/potentialStock.ts` — implement `triggerScan()`, `getTaskStatus()`, etc.
- [X] T041 [US2] Create `PotentialStockMiningPage` in `apps/dsa-web/src/pages/PotentialStockMiningPage.tsx` — manual trigger button with configurable date range selector
- [X] T042 [US2] Add route `/potential-stock-mining` in `apps/dsa-web/src/App.tsx` (lazy-loaded)
- [X] T043 [US2] Add nav item "潜力标的" in `apps/dsa-web/src/components/layout/SidebarNav.tsx`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work — users can trigger scans via CLI or Web, and scheduled scans run automatically. All data persisted as JSON files.

---

## Phase 5: User Story 3 — 查看与跟踪潜力标的清单 (Priority: P2)

**Goal**: 用户可以在 Web 工作台中查看历史潜力标的清单，包括触发事件、核心逻辑、风险提示、优先级分级，并对标的进行纳入观察、跟踪、剔除等状态管理。

**Independent Test**: 手动构造几条筛选结果 JSON 文件放入 `data/potential_stock_mining/results/`，验证 Web 页面能正确展示清单，且状态切换操作更新 `targets.json`。

### Implementation for User Story 3 — API

- [X] T044 [US3] Implement `GET /api/v1/potential-stock/results` in `potential_stock.py` — paginated list with event_type, rating_level, date range filters, backed by `MiningFileStore.list_results()`
- [X] T045 [US3] Implement `GET /api/v1/potential-stock/results/{id}` — full report detail with Markdown content, read from file store
- [X] T046 [US3] Implement `GET /api/v1/potential-stock/targets` — tracked targets list, read from `targets.json`
- [X] T047 [US3] Implement `PUT /api/v1/potential-stock/targets/{stock_code}/status` — update tracking status via `MiningFileStore.update_target_status()`

### Implementation for User Story 3 — Web Frontend

- [X] T048 [P] [US3] Create `MiningResultTable` component in `apps/dsa-web/src/components/potential-stock-mining/MiningResultTable.tsx` — paginated table with columns: stock, event type, priority, rating, score, date
- [X] T049 [P] [US3] Create `TargetDetailModal` component in `apps/dsa-web/src/components/potential-stock-mining/TargetDetailModal.tsx` — full report view with Markdown rendering
- [X] T050 [US3] Integrate results list into `PotentialStockMiningPage` — fetch and display screening results after scan completes
- [X] T051 [US3] Add status management UI (Observe / Track / Remove dropdown) in the results table and detail view
- [ ] T052 [US3] Add filter controls (event type, rating level, date range) to the results page

**Checkpoint**: At this point, User Stories 1, 2, AND 3 work — users can see past results, view detailed reports, and manage tracking status.

---

## Phase 6: User Story 4 — 赛道定向挖掘 (Priority: P3)

**Goal**: 用户可以指定特定产业赛道，系统定向筛选该赛道相关的跨界转型标的，并支持历史回溯验证。

**Independent Test**: 配置一个已知的赛道关键词和一支匹配的历史公告标的，运行赛道定向扫描，验证标的被正确命中。

### Implementation for User Story 4

- [X] T053 [P] [US4] Implement `IndustryKnowledgeBase` service in `src/potential_stock_mining/industry_knowledge_base.py` — load sector definitions from `config/industry_kb.yaml`, provide keyword matching
- [ ] T054 [US4] Implement sector-based filtering in `signal_identifier.py` — cross-reference identified signals against industry KB keywords/products
- [X] T055 [US4] Wire `--sector` CLI argument to orchestrator — passes through to `run_potential_stock_mining()` and eventually `screening_orchestrator.run_scan()`
- [X] T056 [US4] Implement `GET /api/v1/potential-stock/sectors` — list available sectors and their metadata
- [ ] T057 [US4] Create `IndustryKbEditor` component in `apps/dsa-web/src/components/potential-stock-mining/IndustryKbEditor.tsx` — sector management form
- [ ] T058 [US4] Add sector filter UI to the trigger card (`MiningTriggerCard`)

**Checkpoint**: At this point, ALL user stories are functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T059 [P] Review and update `docs/` — add potential stock mining user guide
- [ ] T060 Update `AGENTS.md` if AI collaboration rules are affected by new CLI/config
- [X] T061 Validate all config entries are documented in `.env.example` with descriptions
- [ ] T062 Run `scripts/check_ai_assets.py` to ensure governance alignment
- [X] T063 Add `--potential-stock-mining` to the CLI help examples in `main.py` epilog
- [X] T064 Verify backward compatibility — existing `main.py` modes (--market-review, --backtest, --serve) continue to work unchanged (Mode 4 is independent)
- [ ] T065 Run `quickstart.md` validation scenarios V1-V8

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — scheduling layer on top of core pipeline
- **User Story 2 (Phase 4)**: Depends on Foundational — CLI/Web trigger. Can run in parallel with US1
- **User Story 3 (Phase 5)**: Depends on Foundational + US2 (API + Web routes must exist)
- **User Story 4 (Phase 6)**: Depends on Foundational + US1 signal identifier — extend existing pipeline
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational. No dependencies on other stories.
- **User Story 2 (P1)**: Can start after Foundational. No dependencies on other stories. **Can run in parallel with US1.**
- **User Story 3 (P2)**: Depends on Foundational + US2 (API wiring). API endpoints (T044-T047) can start early.
- **User Story 4 (P3)**: Depends on Foundational + US1 signal identifier.

### Within Each User Story

- Models before services
- Services before endpoints
- Backend before frontend
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks T001-T006: T004 independent of others
- Foundational tasks T007-T021: Extensive parallelism (models, file store, pipeline modules are independent)
- US1 tasks T022-T028: T022 and T023 can run in parallel
- US2 tasks T029-T043: CLI (T029-T034) and API (T035-T039) and Frontend (T040-T043) are partially independent
- US3 tasks T044-T052: API (T044-T047) and Frontend (T048-T052) can run independently
- US4 tasks T053-T058: Knowledge base service (T053) and UI (T057) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch data layer tasks together:
Task: T007 Create dataclass models in models.py
Task: T008 Create MiningFileStore in file_store.py
Task: T009 Implement query methods in file_store.py
Task: T010 Implement tracking methods in file_store.py

# Launch all pipeline modules together:
Task: T011 Create announcement_fetcher.py
Task: T012 Create signal_identifier.py
Task: T013 Create pseudo_transformation.py
Task: T014 Create fundamental_filter.py
Task: T015 Create industry_scorer.py
Task: T016 Create report_generator.py
Task: T017 Create screening_orchestrator.py
Task: T020 Create rule_engine.py
```

## Parallel Example: User Story 1 + User Story 2

```bash
# US1: Scheduled scan automation
Task: T022 Add run_potential_stock_mining() entry function
Task: T023 Implement scheduled scan integration
Task: T025 Implement scan deduplication

# US2: Manual trigger (runs in parallel with US1)
Task: T029-T034 Implement CLI arguments
Task: T035-T039 Implement Web API endpoints
Task: T040-T043 Implement Web frontend
```

## Parallel Example: User Story 3

```bash
# Launch API and Frontend together:
Task: T044-T047 Implement API endpoints for results and targets
Task: T048-T052 Implement frontend components and pages
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 CLI Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — includes `MiningFileStore` + all pipeline modules)
3. Complete Phase 3: User Story 1 — Scheduled scanning pipeline
4. Complete CLI portion of User Story 2 (T029-T034) — `--potential-stock-mining` command
5. **STOP and VALIDATE**: Run `quickstart.md` V1, V2, V3, V6
6. Deploy/demo if ready

### Incremental Delivery

1. **Setup + Foundational** → Core pipeline + file store ready
2. **US1 + US2 CLI** → CLI MVP (scannable, results in JSON files, console report) → **Deploy MVP**
3. **US2 Web (API + UI)** → Web trigger capability → **Deploy V2**
4. **US3** → Result viewing and tracking → **Deploy V3**
5. **US4** → Sector-specific mining → **Deploy V4**
6. **Polish** → Documentation, validation, compatibility checks

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (scheduling) + User Story 4 (sector, extends US1)
   - Developer B: User Story 2 CLI + API
   - Developer C: User Story 2 Frontend + User Story 3
3. All merge independently after Foundational is complete

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The cninfo API orgId resolution (T011) is the primary technical risk — validate early
- Reuse existing `DataFetcherManager.get_fundamental_context()` for T014 rather than adding new data sources
- File store directory `data/potential_stock_mining/` is git-ignored by default (runtime data)
- Config YAML files in `config/` are checked into git (shared configuration)
