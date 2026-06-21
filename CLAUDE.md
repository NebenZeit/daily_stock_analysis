# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **AI Governance:** [`AGENTS.md`](./AGENTS.md) is the single source of truth for repository AI collaboration rules — commit policy, PR title conventions, contribution quality standards, and AI asset management. This file complements it with architecture and command reference.

## Quick Start

```bash
# Backend — analyze stocks
python main.py --stocks 600519    # Analyze single A-share stock
python main.py --market-review    # Market review only
python main.py --stocks 600519,AAPL --no-market-review --no-notify  # Quick test

# Web server
python main.py --serve-only       # FastAPI backend only
python main.py --serve            # API + execute analysis
python webui.py                   # Shorthand for --serve-only

# With uvicorn directly
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## Common Commands

### Backend (Python)

| Command | Description |
|---------|-------------|
| `python main.py` | Full analysis — market review + stocks from `STOCK_LIST` env |
| `python main.py --debug` | Debug logging |
| `python main.py --dry-run` | Fetch data only, skip AI analysis |
| `python main.py --stocks 600519,hk00700,AAPL` | Analyze specific stocks (A/HK/US mixed) |
| `python main.py --single-notify` | Push each stock result individually |
| `python main.py --serve-only` | Start API server only |
| `python main.py --serve` | API server + run analysis |
| `python main.py --check-notify` | Diagnostics: test notification channels |
| `python main.py --check-config` | Diagnostics: validate configuration |

### Tests

```bash
# Python tests
pytest                                       # All offline tests (-m "not network")
pytest -m "unit"                             # Fast offline unit tests only
pytest -m "integration"                      # Integration tests (no network needed)
pytest -m "network"                          # Tests requiring external services
pytest tests/test_auth.py -v                 # Single test file
pytest tests/test_agent_executor.py -k "sse" # Specific test by keyword

# Quick validation gate
./scripts/ci_gate.sh                         # syntax + flake8 + deterministic tests + offline suite
./scripts/ci_gate.sh syntax                  # Just Python compile checks
./scripts/ci_gate.sh offline-tests           # All non-network tests

# Integration test scenarios
./scripts/test.sh quick                      # Fast: one stock, no notify
./scripts/test.sh market                     # Market review only
./scripts/test.sh a-stock                    # A-share (600519, 000001)
./scripts/test.sh hk-stock                   # Hong Kong (hk00700, hk09988)
./scripts/test.sh us-stock                   # US (AAPL, TSLA)
./scripts/test.sh mixed                      # All markets combined
./scripts/test.sh dry-run                    # Data fetch only
./scripts/test.sh full                       # Complete pipeline
./scripts/test.sh all                        # All standalone unit tests
```

### Lint & Format

```bash
# Python
flake8 . --count --select=E9,F63,F7,F82     # Error-level only
black --check . --line-length=120            # Style check
black . --line-length=120                    # Auto-format

# Web frontend
cd apps/dsa-web
npm ci
npm run lint                                 # ESLint
npm run build                                # TypeScript + Vite build
```

### Web Frontend

```bash
cd apps/dsa-web
npm ci                                       # Install dependencies
npm run dev                                  # Dev server (Vite)
npm run build                                # Production build
npm run test                                 # Vitest unit tests
npm run test:smoke                           # Playwright E2E tests
```

### Desktop (Electron)

```bash
cd apps/dsa-desktop
npm ci
npm run dev                                  # Dev mode
./scripts/build-desktop.ps1                  # Package (Windows)
```

### Docker

```bash
docker-compose -f ./docker/docker-compose.yml up -d           # Scheduled analysis
docker-compose -f ./docker/docker-compose.yml up -d server    # API server only
```

## Architecture Overview

### System Flow

```
STOCK_LIST → Data Providers → Technical Analysis + News Search
    → LLM Analysis (per-stock) → Reports → Notifications
    → Market Review (index-level) → Report → Notifications
```

### Key Modules

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| Entry | `main.py` | CLI, orchestration, scheduling |
| API | `api/` | FastAPI app, v1 endpoints, auth middlewares |
| Core | `src/core/` | Market review, backtest engine, strategy, trading calendar |
| Analysis | `src/analyzer.py`, `src/market_analyzer.py` | AI-powered stock/market analysis |
| Agent | `src/agent/` | Multi-agent LLM system: orchestrator, executor, skill router, strategy agents (technical, decision, intel, risk, portfolio) |
| Config | `src/config.py` | Single `@dataclass` config loaded from `.env` |
| Data | `data_provider/` | Data source adapters with fallback chain (efinance → akshare → tushare → pytdx → baostock → yfinance) |
| Notifications | `src/notification_sender/` | 14+ channels (wecom, feishu, telegram, discord, slack, email, etc.) |
| Schemas | `src/schemas/` | Pydantic/marshmallow schemas for reports, context packs, market light |
| Repositories | `src/repositories/` | SQLAlchemy data access (analysis, alerts, portfolio, backtest) |
| Web Frontend | `apps/dsa-web/` | React 19 + Vite + TypeScript + Tailwind CSS 4 |
| Desktop | `apps/dsa-desktop/` | Electron shell wrapping the web app |
| Bot | `bot/` | Chat bot interface for interactive stock queries |
| Strategies | `strategies/` | YAML-defined trading strategies (MA golden cross, Chan theory, wave, etc.) |
| Docs | `docs/` | User guides, changelog, deployment instructions |
| Workflows | `.github/workflows/` | CI, daily analysis (00-daily-analysis.yml), Docker publish, release |
| Scripts | `scripts/` | Build, test, and utility scripts |

### Data Provider Fallback Chain

Stock data retrieval follows priority order: `efinance` → `akshare` → `tushare` → `pytdx` → `baostock` → `yfinance`. Each fetcher is a class in `data_provider/` with standardized methods (`get_realtime_quote`, `get_daily_history`, `get_capital_flow`, etc.).

### Agent System (`src/agent/`)

The multi-agent framework uses specialized agents for different analysis dimensions:
- **Technical Agent** — MA/volume/price pattern analysis
- **Decision Agent** — Buy/sell signals, position sizing
- **Intel Agent** — News sentiment, catalysts, risk alerts
- **Risk Agent** — Stop-loss, portfolio risk
- **Portfolio Agent** — Position management

Agents communicate through an orchestrator, use shared tools (`src/agent/tools/`), and follow skill-based routing (`src/agent/skills/`).

### Notification System

Reports can be sent to multiple channels simultaneously. Each channel has a dedicated sender in `src/notification_sender/`. Routing and noise control are configured via `NOTIFICATION_ROUTES` and `NOTIFICATION_SEVERITY_*` env vars.

### Database

SQLAlchemy ORM. Key tables: analysis history (`analysis_repo`), alerts (`alert_repo`), portfolio positions (`portfolio_repo`), backtest results (`backtest_repo`), stock metadata (`stock_repo`).

### Configuration

All configuration flows through `src/config.py`'s `Config` dataclass, loaded from `.env` via `python-dotenv`. `.env.example` documents every variable. The `src/core/config_manager.py` provides runtime reconfiguration for Web users.

<!-- SPECKIT START -->
For additional context about the current feature work, read the implementation plan:
`specs/001-potential-stock-mining/plan.md`

Design artifacts:
- `specs/001-potential-stock-mining/research.md` — Technical research
- `specs/001-potential-stock-mining/data-model.md` — Data model design
- `specs/001-potential-stock-mining/contracts/` — Interface contracts (CLI, API, report schema)
- `specs/001-potential-stock-mining/quickstart.md` — Validation scenarios
<!-- SPECKIT END -->
