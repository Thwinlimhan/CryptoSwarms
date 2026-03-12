# CryptoSwarms Complete Setup Guide

This guide is the canonical runbook to get the app and dashboard running locally.

## 1) Prerequisites

- OS: Windows 11 + PowerShell 7 (project is currently Windows-first in scripts/Makefile).
- Python: 3.12+ (3.13 is used in existing examples).
- Docker Desktop: latest stable, with Compose v2 enabled.
- Git.
- Optional for local LLM service:
  - NVIDIA GPU + NVIDIA Container Toolkit (for `sglang` container).

## 2) Clone and enter project

```powershell
git clone <your-repo-url> CryptoSwarms
cd CryptoSwarms
```

## 3) Configure environment

Create local env file from template:

```powershell
Copy-Item .env.example .env
```

Minimum values to verify in `.env`:

- `DB_PASSWORD`
- `NEO4J_PASSWORD`
- `MC_USER`
- `MC_PASS`
- `MC_API_KEY`
- `DEEPFLOW_ENABLED=false` (keep disabled unless you run observability profile)

## 4) Python environment

```powershell
C:\Users\thwin\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e . pytest
```

## 5) Start core services (recommended path)

Start API + dashboard + required datastores:

```powershell
docker compose up -d mission-control swarm-api redis timescaledb neo4j qdrant
```

Notes:
- `mission-control` serves dashboard at port `3000`.
- `swarm-api` serves app/API at port `8000`.
- `sglang` is a hard dependency of `swarm-api` in current compose; include it if needed:

```powershell
docker compose up -d sglang
```

If you do not have GPU for `sglang`, run API outside Docker (Section 6) and keep compose for dashboard/datastores.

## 6) Start API directly from Python (no containerized API)

Use this mode when Docker build/runtime is constrained or `sglang` is unavailable:

```powershell
.\.venv\Scripts\python.exe -m api.main
```

To enable HTTPS for the local API, set both `SSL_CERTFILE` and `SSL_KEYFILE` in `.env` before starting the server.

API base URL: `https://localhost:8000` (with TLS enabled) or `http://localhost:8000` (default without certs)

## 7) Access points

- Mission Control dashboard: `http://localhost:3000`
- API docs (Swagger): `https://localhost:8000/docs` when TLS is enabled, otherwise `http://localhost:8000/docs`
- Operator dashboard page (served by API): `https://localhost:8000/dashboard` when TLS is enabled, otherwise `http://localhost:8000/dashboard`

Key API health/insight endpoints:

- `GET /healthz`
- `GET /api/dashboard/overview`
- `GET /api/dashboard/insights?lookback_hours=24`
- `GET /api/decision/debate-preview`
- `GET /api/decision/dag-preview`
- `GET /api/decision/dag-stats`

### 6A) Generate localhost certs for HTTPS

Use the bundled PowerShell helper to create PEM files for Uvicorn:

```powershell
pwsh -File scripts\new_localhost_tls_cert.ps1
```

Then set in `.env`:

```dotenv
SSL_CERTFILE=certs/localhost.pem
SSL_KEYFILE=certs/localhost-key.pem
```
## 8) Validate installation

Run core tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run high-signal operational checks:

```powershell
.\.venv\Scripts\python.exe scripts\run_phase1_smoke.py
.\.venv\Scripts\python.exe scripts\check_backtest_runtimes.py
```

For strict runtime backtest gate:

```powershell
$env:REQUIRE_BACKTEST_RUNTIMES='true'
.\.venv\Scripts\python.exe scripts\check_backtest_runtimes.py
```

## 9) Run key workflows

Research and evolution:

```powershell
.\.venv\Scripts\python.exe scripts\run_research_factory.py
.\.venv\Scripts\python.exe scripts\run_skill_factory.py
.\.venv\Scripts\python.exe scripts\run_evolution_autoresearch.py
```

Crypto strategy pack:

```powershell
.\.venv\Scripts\python.exe scripts\run_crypto_strategy_pack.py
```

Paper ledger job:

```powershell
.\.venv\Scripts\python.exe scripts\run_paper_ledger_job.py
```

## 10) Optional observability (DeepFlow)

Only run this if you intentionally enable observability.

Start:

```powershell
docker compose --profile observability up -d deepflow-server deepflow-agent
```

Preflight:

```powershell
.\.venv\Scripts\python.exe scripts\run_deepflow_preflight.py
```

Important:
- DeepFlow agent needs a reachable DeepFlow controller/server.
- If controller is not reachable, agent logs gRPC connection errors by design.
- Keep `DEEPFLOW_ENABLED=false` when observability stack is not fully provisioned.

## 11) Troubleshooting

### A) `swarm-api` Docker build fails at `apt-get update` timeout

Use hardened rebuild script:

```powershell
pwsh -File scripts/run_swarm_api_build.ps1
```

Then retry:

```powershell
docker compose up -d swarm-api
```

### B) Mission Control cannot connect to API

Check:
- `swarm-api` is healthy on `https://localhost:8000/healthz` when TLS is enabled, otherwise `http://localhost:8000/healthz`
- compose env values for gateway:
  - `NEXT_PUBLIC_GATEWAY_HOST`
  - `NEXT_PUBLIC_GATEWAY_PORT`
  - `NEXT_PUBLIC_GATEWAY_PROTOCOL`

Restart dashboard:

```powershell
docker compose up -d --build mission-control
```

### C) DeepFlow server YAML indentation error (tab character)

If logs show:
- `Unmarshal yaml(/etc/server.yaml) error: ... found a tab character ...`

Fix `infra/deepflow/server.yaml` by replacing tabs with spaces, then restart observability services.

### D) Mission Control build fails with Docker Hub TLS timeout

If you see errors like `failed to fetch oauth token` or `TLS handshake timeout`, run:

```powershell
pwsh -File scripts/run_mission_control_build.ps1
docker compose up -d mission-control
```
## 12) Stop and clean up

Stop services:

```powershell
docker compose down
```

Stop and remove volumes (destructive):

```powershell
docker compose down -v
```

## 13) Recommended day-1 startup sequence

```powershell
Copy-Item .env.example .env
C:\Users\thwin\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . pytest
docker compose up -d mission-control swarm-api redis timescaledb neo4j qdrant sglang
.\.venv\Scripts\python.exe -m pytest -q
```
