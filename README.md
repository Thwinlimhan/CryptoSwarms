# CryptoSwarms

Phase-oriented implementation scaffold for `Crypto swarm v6`.

## Current status

- Phase 0: infrastructure scaffold in place (compose, env template, CI, task runner).
- Phase 1: vertical slice includes scanner loop, runtime adapters, and paper promotion report job.
- Phase 2+: core checklist tracked in `docs/MASTER_IMPLEMENTATION_CHECKLIST_V6.md`.

## Project layout

- `cryptoswarms/`: core orchestration domain modules.
- `agents/`: swarm agents grouped by domain (`research`, `backtest`, `execution`, `evolution`, `orchestration`).
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
.\.venv\Scripts\python.exe scripts\run_skill_factory.py
.\.venv\Scripts\python.exe scripts\run_skill_factory_readtheskill.py
.\.venv\Scripts\python.exe scripts\run_skill_factory_bnbchain.py
.\.venv\Scripts\python.exe scripts\run_skill_factory_cryptoskills.py
.\.venv\Scripts\python.exe scripts\run_crypto_strategy_pack.py
.\.venv\Scripts\python.exe scripts\run_evolution_autoresearch.py
.\.venv\Scripts\python.exe scripts\check_backtest_runtimes.py
.\.venv\Scripts\python.exe scripts\run_deepflow_preflight.py
pwsh -File scripts/run_swarm_api_build.ps1
docker compose up -d mission-control swarm-api redis timescaledb
```

## Build troubleshooting

- If `swarm-api` fails on `apt-get update` timeout, run: `pwsh -File scripts/run_swarm_api_build.ps1`.
- The Dockerfile now forces IPv4 and apt retries/timeouts to reduce flaky Debian mirror failures.

## Mission Control Scope

- Mission Control upstream is OpenClaw-first. In this repo we use it as an operator UI for CryptoSwarms with custom branding and API wiring.
- Some OpenClaw-specific panels remain upstream and require deeper fork-level refactor to fully remove.



## DeepFlow Agent
- DeepFlow is optional and isolated behind the `observability` profile.
- Controller + agent startup: `docker compose --profile observability up -d deepflow-server deepflow-agent`
- DeepFlow agent config file: `infra/deepflow/deepflow-agent.yaml`
- If you do not run DeepFlow, keep `DEEPFLOW_ENABLED=false` to avoid false health expectations.
- Note: `deepflowce/deepflow-server` still expects controller backing dependencies (`mysql`, `redis`, `clickhouse`) and Kubernetes-style election env. For local Docker-only runs, keep DeepFlow disabled or point the agent at an external controller.

## Operator dashboard

- Interactive deck: `https://localhost:8000/dashboard`
- Insight API: `GET /api/dashboard/insights?lookback_hours=24`
- Overview API: `GET /api/dashboard/overview`
- Debate preview API: `GET /api/decision/debate-preview`
- DAG preview API: `GET /api/decision/dag-preview`
- DAG stats API: `GET /api/decision/dag-stats`

### Local HTTPS

Run `pwsh -File scripts\new_localhost_tls_cert.ps1`, then set both `SSL_CERTFILE` and `SSL_KEYFILE` in `.env` to enable TLS for the FastAPI server on port `8000`. When those values are blank, the API still serves plain HTTP.
## Governance highlights

- Strict D10 runtime CI checks enforce real `vectorbt` + `jesse` availability (`REQUIRE_BACKTEST_RUNTIMES=true`).
- Paper-to-live promotion uses hard scorecard gates: minimum sample size, out-of-sample stability, and drawdown constraints.
- Live execution requires explicit post-trade attribution (`hypothesis_id`, optimizer run/candidate, source, strategy).
- Strategy count is capped at one unless durability across regimes is proven.
- Agentic Research Factory combines connector signals with books/papers knowledge and emits traceable backtest requests.
- Subagent delegation is active for parallel connector fetch in research factory.
- Skill Factory converts validated knowledge into reusable `skill`, `playbook`, and `tool_spec` artifacts for other agents.
- Skill lifecycle controls are active: create/patch/edit + hub/audit flow with credential filtering.
- Progressive skill loading is available for token-efficient retrieval in research generation.
- ReadTheSkill crypto catalog is available as a curated ingest source via `scripts/run_skill_factory_readtheskill.py`.
- BNB Chain skills catalog is available as a curated ingest source via `scripts/run_skill_factory_bnbchain.py`.
- CryptoSkills.dev catalog is available as a curated ingest source via `scripts/run_skill_factory_cryptoskills.py`.
- Decision framework is active in research/promotion loops: base-rate priors, Bayesian updates, expected value after costs, and fractional Kelly sizing.
- Decision Council orchestration adds deterministic stages, debate rounds, weighted aggregation, and governor final gate for high-stakes decisions.
- DAG memory is integrated for bounded context recall and decision checkpoint persistence, now saved to `data/agent_memory_dag.json` for cross-run reuse.
- Survivorship-bias control is supported through a failure ledger that can penalize over-promoted strategy families.
- Crypto-fit strategy modules included:
  - pairs / spread mean reversion
  - volatility compression breakout
  - cross-sectional momentum rotation

## References

- Agentic background R&D workflow: `docs/AGENTIC_RESEARCH_FACTORY.md`
- Decision framework modules: `docs/DECISION_FRAMEWORK.md`
- Decision Council orchestration: `docs/DECISION_COUNCIL_ORCHESTRATION.md`

## Verification

Run `pytest -q` for the latest local status.




## Complete setup guide

See [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for end-to-end setup, startup, validation, and troubleshooting for API + dashboard + optional observability.


- If mission-control build fails with Docker Hub TLS handshake timeout, run: pwsh -File scripts/run_mission_control_build.ps1.
