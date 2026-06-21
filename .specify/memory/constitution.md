<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: N/A (first fill)
- Added sections:
  - Principle I: Stability-First Development
  - Principle II: Contract & Compatibility Preservation
  - Principle III: Multi-Source Data Resilience
  - Principle IV: Documentation-Driven Change
  - Principle V: Minimal Surface Change + Validated Delivery
  - Section 2: Additional Constraints — Multi-Market & Fallback
  - Section 3: Development Workflow — Review & Quality Gates
- Removed sections: none
- Templates requiring updates:
  - ✓ .specify/templates/spec-template.md (no constitution-specific references)
  - ✓ .specify/templates/plan-template.md (uses generic "Constitution Check" section)
  - ✓ .specify/templates/tasks-template.md (no constitution-specific references)
- Follow-up TODOs: none
-->

# 股票智能分析系统 Constitution

## Core Principles

### I. Stability-First Development (NON-NEGOTIABLE)

Default to stability over opportunistic optimization. Non-task refactoring,
abstraction migrations, infrastructure upgrades, and dependency bumps that are
not directly required by the current task MUST be restrained. Every change MUST
minimize its impact surface — a correct, focused change is strictly preferred
over a "cleaner" change that touches unrelated areas.

**Rationale**: This project integrates multiple data sources, notification
channels, AI models, and deployment modes (GitHub Actions / Docker / local).
Unrelated side-effects in one area can silently break another. Stability-first
is the primary guard against regressions.

### II. Contract & Compatibility Preservation (NON-NEGOTIABLE)

Changes to API endpoints, request/response schemas, report payloads,
notification templates, or CLI arguments MUST verify compatibility across ALL
consumers: backend analysis pipeline, Web frontend, Desktop app, bot, and
external integrations. Default strategy: append new fields, retain deprecated
fields through a compatibility window, and provide explicit migration notes.

**Rationale**: API/Schema contracts are shared across runtimes (Python
backend + TypeScript/React frontend + Electron shell). Silent breaks cascade
across deployment targets and are difficult to catch without explicit
verification.

### III. Multi-Source Data Resilience (NON-NEGOTIABLE)

No single data source failure SHALL crash the analysis pipeline. The data
provider fallback chain MUST be maintained, tested, and extended when adding
new data sources. Timeouts, retries, graceful degradation, and informative
error messages are REQUIRED for every data provider integration. Silent
fallback (returning empty/None without logging) is PROHIBITED.

**Rationale**: The fallback chain (efinance → akshare → tushare → pytdx →
baostock → yfinance) is the project's core reliability pattern. A source may
be rate-limited, down, or removed without notice; the analysis must survive
and report the gap clearly.

### IV. Documentation-Driven Change

Any change that affects user-facing capabilities, CLI behavior, API responses,
deployment procedures, notification formats, report structure, or configuration
semantics MUST synchronize the corresponding documentation. When modifying
bilingual docs (Chinese / English), evaluate whether the counterpart requires
updating. New configuration variables MUST be added to `.env.example` with a
description. Changes to AI governance assets (`AGENTS.md`, `CLAUDE.md`,
`.github/copilot-instructions.md`) MUST run `scripts/check_ai_assets.py`.

**Rationale**: Documentation drift is the most common source of confusion
for new contributors and fork users. Keeping docs in sync with code reduces
support burden and deployment errors.

### V. Minimal Surface Change + Validated Delivery

Only make changes directly required by the current task. Do not bundle
unrelated refactoring, style fixes, or dependency upgrades. Every delivery
MUST include:

- **What** was changed and why
- **Verification status** — which tests/configs/workflows were run and
  their results
- **Unverified items** — what could not be tested and why
- **Risks** — what might break as a side effect
- **Rollback method** — how to revert if the change causes issues

PRs MUST demonstrate understanding of system contracts; supplemental patching
at review time without re-checking the full semantic scope is PROHIBITED.

**Rationale**: This principle enforces accountability and prevents
"drive-by" contributions that leave the codebase in a less maintainable
state than before.

## Additional Constraints — Multi-Market & Fallback

### Market Coverage

The system MUST support concurrent analysis of A-shares (China), Hong Kong
stocks, and US stocks. Stock codes follow the project's prefix convention
(`hk` for HK, no prefix for A-shares). Each market has distinct data source
availability, trading calendars, and holiday schedules — the system MUST
handle these transparently within the same analysis run.

### Data Provider Integrity

- Data source priority and fallback order is defined in `data_provider/`.
  Reordering or adding sources requires updating the fallback documentation.
- A data source returning unexpected data (empty DataFrame, stale date,
  NaN values) SHOULD trigger fallback rather than propagating corrupt data.
- Rate limiting and quota exhaustion MUST be handled gracefully per source.

### Configuration Hygiene

- All configuration MUST flow through `src/config.py`'s `Config` dataclass.
- Hardcoded keys, tokens, paths, model names, port numbers, or environment-
  specific logic in source code is PROHIBITED.
- New configuration entries MUST have sensible defaults or clear "not
  configured" behavior.

### Notification Isolation

- A single notification channel failure MUST NOT block the overall analysis.
- Notification errors SHOULD be logged but not re-raised to the analysis
  pipeline, unless the system is explicitly configured as fail-fast.

## Development Workflow — Review & Quality Gates

### Verification Matrix

Changes MUST be validated according to their surface (mapped from AGENTS.md):

| Change Surface | Minimum Verification |
|----------------|---------------------|
| Python backend | `./scripts/ci_gate.sh` or `pytest -m "not network"` |
| Web frontend | `cd apps/dsa-web && npm ci && npm run lint && npm run build` |
| Desktop app | Web build first, then Electron build |
| API / Schema / Auth | Backend verification + affected client build |
| Docs / governance | Review command/filename accuracy against repo; run `scripts/check_ai_assets.py` |
| Workflows / scripts / Docker | Closest local equivalent; explicit note on untested paths |
| Network / third-party deps | Offline checks first; verify timeout/retry/fallback logic |

### Review Process

- Review order: necessity → relevance → title → description completeness →
  verification evidence → implementation correctness → merge judgement.
- `fix` PRs MUST explain: original problem, root cause, fix point, regression
  risk.
- Merge blockers: correctness/security issues, blocking CI failures, PR body
  contradicting actual diff, missing rollback plan, repeated uncontained
  contract drift.

### AI Collaboration Governance

- `AGENTS.md` is the single source of truth for AI collaboration rules.
- `CLAUDE.md` is a soft-link pointer to `AGENTS.md` for Claude Code
  compatibility.
- `.github/copilot-instructions.md` and `.github/instructions/*` are mirrors;
  `AGENTS.md` takes precedence on conflict.
- No operation that modifies remote state (`git push`, `git tag`, `git pull`,
  `gh pr create`) SHALL be executed without user confirmation.
- Commit messages MUST be in English, MUST NOT include `Co-Authored-By`.

## Governance

This constitution is derived from the project's `AGENTS.md` and `README.md`,
codifying the norms that have evolved through the project's development.
It serves as the non-negotiable framework for all feature work conducted
through the SpecKit workflow.

**Amendment Procedure**:
1. Proposed changes MUST be documented with rationale and migration impact.
2. Amendments require maintainer approval.
3. Version MUST be bumped per semantic versioning rules:
   - MAJOR: backward-incompatible principle removal or redefinition
   - MINOR: new principle or materially expanded guidance
   - PATCH: clarification, wording, typo fixes, non-semantic refinements
4. After amendment, run consistency propagation:
   - Check templates in `.specify/templates/` for alignment
   - Update command files if principle-driven task types change
   - Verify runtime guidance docs for principle references

**Compliance**: All spec, plan, and task artifacts generated by SpecKit
MUST align with these principles. Any deviation must be explicitly noted
with justification in the corresponding artifact.

**Version**: 1.0.0 | **Ratified**: 2026-06-20 | **Last Amended**: 2026-06-20