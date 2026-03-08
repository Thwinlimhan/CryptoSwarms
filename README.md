# CryptoSwarms

Phase-oriented implementation scaffold for `Crypto swarm v6`.

## Current status

- Phase 0: infrastructure scaffold in place (compose, env template, CI, task runner).
- Phase 1: vertical slice includes scanner loop, runtime adapters, and paper promotion report job.
- Phase 2+: core checklist tracked in `docs/MASTER_IMPLEMENTATION_CHECKLIST_V6.md`.

## Project layout

- `cryptoswarms/`: core orchestration domain modules.
- `agents/`: swarm agents grouped by domain (`research`, `backtest`, `execution`, `evolution`).
- `api/`: FastAPI service and health/bridge endpoints.
- `infra/`: infrastructure and schema assets.
- `data/schemas/`: TimescaleDB bootstrap SQL.
- `memory/`: Mem0 + Graphiti integration and memory-quality utilities.
- `strategies/`: strategy hypotheses and candidate definitions.
- `scripts/`: operational scripts for phased runs.
- `docs/`: phase plans and operational notes.
- `tests/`: unit + integration tests.
- `mission-control-upstream/`: cloned upstream Mission Control dashboard.

## Local setup (Windows)

```powershell
C:\Users\thwin\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest
```

## Common commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase1_smoke.py
.\.venv\Scripts\python.exe scripts\run_phase1_loop.py
.\.venv\Scripts\python.exe scripts\run_paper_ledger_job.py
.\.venv\Scripts\python.exe scripts\run_research_camoufox.py
.\.venv\Scripts\python.exe scripts\run_research_factory.py
.\.venv\Scripts\python.exe scripts\run_evolution_autoresearch.py
.\.venv\Scripts\python.exe scripts\check_backtest_runtimes.py
docker compose up -d mission-control swarm-api redis timescaledb
```

## Operator dashboard

- Interactive deck: `http://localhost:8000/dashboard`
- Insight API: `GET /api/dashboard/insights?lookback_hours=24`
- Overview API: `GET /api/dashboard/overview`

## Governance highlights

- Strict D10 runtime CI checks enforce real `vectorbt` + `jesse` availability (`REQUIRE_BACKTEST_RUNTIMES=true`).
- Paper-to-live promotion uses hard scorecard gates: minimum sample size, out-of-sample stability, and drawdown constraints.
- Live execution requires explicit post-trade attribution (`hypothesis_id`, optimizer run/candidate, source, strategy).
- Strategy count is capped at one unless durability across regimes is proven.
- Agentic Research Factory combines connector signals with books/papers knowledge and emits traceable backtest requests.

## References

- Agentic background R&D workflow: `docs/AGENTIC_RESEARCH_FACTORY.md`

## Verification

Run `pytest -q` for the latest local status.
