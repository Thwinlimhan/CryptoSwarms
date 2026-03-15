# 🚀 CryptoSwarms — Implementation Checklist

> **Created:** 2026-03-13  
> **Based on:** [Deep Codebase Review](file:///C:/Users/thwin/.gemini/antigravity/brain/85d10bb4-3168-4a0e-83d9-4324b3bb2d48/cryptoswarms_deep_review.md)  
> **Goal:** Take CryptoSwarms from prototype (C+) to production-ready (A-)

---

## Phase 0 — Critical Security Fixes 🔴
**Estimated effort:** 2–3 hours  
**Priority:** MUST DO before any live exposure

### Task 0.1 — Add API Key Authentication Middleware
- [x] Create file [api/middleware/auth.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/middleware/auth.py)
- [x] Implement [APIKeyMiddleware](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/middleware/auth.py#21-40) that checks `X-API-Key` header on all `/api/*` routes
- [x] Add `API_KEY` to [api/settings.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/settings.py) as a required env variable
- [x] Add `API_KEY` to [.env.example](file:///c:/Users/thwin/Desktop/CryptoSwarms/.env.example) with a placeholder value
- [x] Register middleware in [api/main.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/main.py) after CORS
- [x] Exempt `/api/health/live` and `/api/health/ready` from auth (needed for Docker health checks)
- [x] Add test in `tests/test_api_auth.py` to verify unauthenticated requests get 401

```python
# api/middleware/auth.py — target implementation
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from api.settings import settings

EXEMPT_PATHS = {"/api/health/live", "/api/health/ready"}

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.api_key:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
```

### Task 0.2 — Restrict CORS Origins
- [x] In [api/main.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/main.py), change `allow_origins=["*"]` to a configurable list
- [x] Add `CORS_ORIGINS` to [api/settings.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/settings.py) (default: `"http://localhost:5173,http://127.0.0.1:5173"`)
- [x] Add `CORS_ORIGINS` to [.env.example](file:///c:/Users/thwin/Desktop/CryptoSwarms/.env.example)
- [x] Update the `CORSMiddleware` registration to use `settings.cors_origins.split(",")`

```diff
# api/main.py — target change
 app.add_middleware(
     CORSMiddleware,
-    allow_origins=["*"],
+    allow_origins=settings.cors_origins.split(","),
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
 )
```

### Task 0.3 — Add `httpx` to Dependencies
- [x] Add `"httpx>=0.27.0"` to the `dependencies` list in [pyproject.toml](file:///c:/Users/thwin/Desktop/CryptoSwarms/pyproject.toml)
- [x] Run `pip install -e .` to verify installation

```diff
# pyproject.toml
 dependencies = [
     "fastapi>=0.111.1,<0.115.0",
     "pydantic>=2.7.0",
     "redis>=4.1.4,<5.0.0",
     "asyncpg>=0.29.0",
     "uvicorn>=0.29.0,<0.30.0",
+    "httpx>=0.27.0",
 ]
```

### Task 0.4 — Remove TLS Certs from Repo
- [x] Delete [certs/localhost-key.pem](file:///c:/Users/thwin/Desktop/CryptoSwarms/certs/localhost-key.pem) and [certs/localhost.pem](file:///c:/Users/thwin/Desktop/CryptoSwarms/certs/localhost.pem) from Git tracking
- [x] Run `git rm --cached certs/localhost-key.pem certs/localhost.pem`
- [x] Verify `certs/` is already in [.gitignore](file:///c:/Users/thwin/Desktop/CryptoSwarms/.gitignore) (it is)
- [x] Commit the removal

### Task 0.5 — Sanitize Database DSN Logging
- [x] In [cryptoswarms/adapters/timescale_sink.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/cryptoswarms/adapters/timescale_sink.py) line 29, mask the password in the log:
```diff
-    logger.info("TimescaleSink connected to %s", self._dsn.split("@")[-1])
+    logger.info("TimescaleSink connected to %s", self._dsn.split("@")[-1] if "@" in self._dsn else "***")
```

---

## Phase 1 — Dead Code Removal 🧹
**Estimated effort:** 30 minutes  
**Priority:** HIGH — reduces confusion and repo size

### Task 1.1 — Remove Orphaned Root Files
- [x] Delete [hyperliquid_api.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/hyperliquid_api.py) (230 lines, not imported by any module)
- [x] Delete [polymarket_api.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/polymarket_api.py) (247 lines, not imported by any module)
- [x] Delete [claude_code_integration.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/claude_code_integration.py) (330 lines, not imported by any module)
- [x] Delete [moon_dev_tui.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/moon_dev_tui.py) (2,112 lines, not imported by any module)
- [x] Delete [run_moon_dev_tui.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/run_moon_dev_tui.py) (launcher for dead TUI)
- [x] Delete [requirements_tui.txt](file:///c:/Users/thwin/Desktop/CryptoSwarms/requirements_tui.txt) (dependencies for dead TUI)
- [x] Delete [README_TUI.md](file:///c:/Users/thwin/Desktop/CryptoSwarms/README_TUI.md) (docs for dead TUI)

> [!TIP]
> Before deleting, do a final grep to confirm nothing imports them:
> ```powershell
> findstr /S /M "from hyperliquid_api" *.py
> findstr /S /M "from polymarket_api" *.py
> findstr /S /M "from claude_code_integration" *.py
> findstr /S /M "from moon_dev_tui" *.py
> ```

### Task 1.2 — Remove Large Dump Files
- [x] Delete [cryptoswarms_full_codebase.md](file:///c:/Users/thwin/Desktop/CryptoSwarms/cryptoswarms_full_codebase.md) (814KB dumped codebase — no purpose in repo)
- [x] Move `Crypto swarm v6.txt` (81KB spec) to [docs/architecture/crypto_swarm_v6_spec.txt](file:///c:/Users/thwin/Desktop/CryptoSwarms/docs/architecture/crypto_swarm_v6_spec.txt)

### Task 1.3 — Clean Empty Placeholder Directories
- [x] Delete [services/README.md](file:///c:/Users/thwin/Desktop/CryptoSwarms/services/README.md) (empty placeholder — 160 bytes, says "TODO")
- [x] Consider deleting the `services/` directory entirely or adding real content
- [x] Delete [mission-control/Dockerfile](file:///c:/Users/thwin/Desktop/CryptoSwarms/mission-control/Dockerfile) + [mission-control/index.html](file:///c:/Users/thwin/Desktop/CryptoSwarms/mission-control/index.html) (stub — 69 bytes total, superseded by `mission-control-upstream/`)

### Task 1.4 — Delete Duplicate Functions in [api/main.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/main.py)
- [ ] Remove standalone `_fetch_redis_heartbeats()` (lines 120–130) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_signal_counts()` (lines 133–154) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_equity_curve()` (lines 157–179) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_current_regime()` (lines 182–209) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_pending_validation()` (lines 212–239) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_latest_risk_event()` (lines 242–266) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_dashboard_insight_inputs()` (lines 269–330) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [x] Remove standalone `_fetch_live_trade_traces()` (lines 333–368) — replaced by [DashboardRepository](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#51-295)
- [ ] Remove standalone [_parse_heartbeat()](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#32-42) (lines 101–110) — duplicate of [dashboard_repository.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py)
- [ ] Remove duplicate [_timescale_dsn()](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dashboard_repository.py#44-49) (lines 113–117) — keep only [_timescale_dsn_str()](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/dependencies.py#16-21) at line 65
- [x] Run tests: `.venv\Scripts\python.exe -m pytest -q`

### Task 1.5 — Remove Inline HTML Dashboard
- [x] Delete the entire `/dashboard` route and its HTML string (lines 996–1279 in [api/main.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/main.py))
- [x] Remove `from fastapi.responses import HTMLResponse` if no longer used
- [x] The React frontend at `frontend/` is the canonical dashboard

---

## Phase 2 — API Decomposition 🏗️
**Estimated effort:** 3–4 hours  
**Priority:** HIGH — [api/main.py](file:///c:/Users/thwin/Desktop/CryptoSwarms/api/main.py) is currently 1,310 lines

### Task 2.1 — Create Route Module Structure
- [x] Create directory `api/routes/`
- [x] Create `api/routes/__init__.py`
- [x] Create `api/routes/health.py` — move health endpoints
- [x] Create `api/routes/dashboard.py` — move overview, insights, equity-curve, regime, validation, agents/status
- [x] Create `api/routes/agents.py` — move agents/control, runner-status, research/latest
- [x] Create `api/routes/backtest.py` — move backtest/strategies, backtest/results
- [x] Create `api/routes/decision.py` — move debate-preview, dag-preview, dag-stats, attribution-lineage
- [x] Create `api/routes/orchestration.py` — move runtime-preview, subagents-preview
- [x] Create `api/routes/costs.py` — move costs/budget, costs/daily
- [x] Create `api/routes/tracing.py` — move tracing/status, paper-mcp/status

### Task 2.2 — Extract Shared Dependencies
- [x] Create `api/dependencies.py` with shared instances:
  ```python
  # api/dependencies.py
  from cryptoswarms.memory_dag import MemoryDag
  from agents.orchestration.dag_memory_bridge import DagMemoryBridge
  from api.dashboard_repository import DashboardRepository
  from cryptoswarms.agent_runner import AgentRunner
  
  REGISTERED_AGENTS = ["market_scanner", "validation_pipeline", "risk_monitor"]
  _DECISION_MEMORY_DAG = MemoryDag()
  _DAG_BRIDGE = DagMemoryBridge(_DECISION_MEMORY_DAG)
  _DASHBOARD_REPO = DashboardRepository(REGISTERED_AGENTS)
  # ... etc
  ```
- [x] Update route modules to import from `api.dependencies`

### Task 2.3 — Register Route Modules as APIRouter
- [x] Each route file uses `APIRouter(prefix="/api/...", tags=[...])`
- [x] `api/main.py` becomes ~50 lines: app creation, middleware, lifespan, and `app.include_router(...)` calls
- [x] Run all tests to verify nothing broke

### Task 2.4 — Target Structure After Decomposition
```
api/
├── __init__.py
├── main.py              # ~50 lines: app factory, middleware, lifespan
├── settings.py           # unchanged
├── dependencies.py       # shared singletons and helpers
├── dashboard_repository.py  # unchanged
├── middleware/
│   └── auth.py           # from Phase 0
└── routes/
    ├── __init__.py
    ├── health.py          # /api/health/*
    ├── dashboard.py       # /api/dashboard/*, /api/portfolio/*, /api/regime/*
    ├── agents.py          # /api/agents/*, /api/research/*
    ├── backtest.py        # /api/backtest/*
    ├── decision.py        # /api/decision/*
    ├── orchestration.py   # /api/orchestration/*
    ├── costs.py           # /api/costs/*
    └── tracing.py         # /api/tracing/*, /api/paper-mcp/*
```

---

## Phase 3 — Frontend Hardening 🖥️
**Estimated effort:** 2 hours  
**Priority:** MEDIUM

### Task 3.1 — Extract API URL to Environment Variable
- [x] Create `frontend/.env` with `VITE_API_URL=http://127.0.0.1:8000`
- [x] Create `frontend/.env.example` with `VITE_API_URL=http://127.0.0.1:8000`
- [x] Add `frontend/.env` to `frontend/.gitignore`
- [x] Create `frontend/src/config.ts`:
  ```typescript
  export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  ```
- [x] Update ALL view files to import from config instead of hardcoding:
  - [x] `App.tsx` — line 109
  - [x] `Dashboard.tsx` — line 4
  - [x] `Backtest.tsx`
  - [x] `Costs.tsx`
  - [x] `Council.tsx`
  - [x] `MemoryDAG.tsx`
  - [x] `Attribution.tsx`
  - [x] `Orchestration.tsx`
  - [x] `ResearchHub.tsx`
  - [x] `DataSources.tsx`
  - [x] `CodeViewer.tsx`
  - [x] `Settings.tsx`

### Task 3.2 — Add React Error Boundary
- [x] Create `frontend/src/components/ErrorBoundary.tsx`
- [x] Wrap `<Routes>` in `App.tsx` with the error boundary
- [x] Display a user-friendly error message with a "Reload" button

```typescript
// frontend/src/components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';

interface Props { children: ReactNode; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="border-box" style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>SYSTEM_ERROR</h2>
          <p className="text-muted">{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>RELOAD</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### Task 3.3 — Create Shared API Hook
- [x] Create `frontend/src/hooks/useApi.ts` — a reusable fetch hook with error handling, loading state, and auto-refresh
- [x] Refactor `Dashboard.tsx`, `ResearchHub.tsx`, `Backtest.tsx` to use the shared hook
- [x] This eliminates the repeated `useEffect` + `fetch` + `setInterval` + `try/catch` pattern in every view

```typescript
// frontend/src/hooks/useApi.ts
import { useState, useEffect } from 'react';
import { API_URL } from '../config';

export function useApi<T>(path: string, intervalMs = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_URL}${path}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setData(await res.json());
        setError(null);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const id = setInterval(fetchData, intervalMs);
    return () => clearInterval(id);
  }, [path, intervalMs]);

  return { data, loading, error };
}
```

### Task 3.4 — Add Frontend to Docker Compose
- [x] Create `frontend/Dockerfile`:
  ```dockerfile
  FROM node:22-alpine AS build
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci
  COPY . .
  RUN npm run build
  
  FROM nginx:alpine
  COPY --from=build /app/dist /usr/share/nginx/html
  COPY nginx.conf /etc/nginx/conf.d/default.conf
  EXPOSE 80
  ```
- [x] Create `frontend/nginx.conf` with SPA fallback routing
- [x] Add service to `docker-compose.yml`:
  ```yaml
  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - swarm-api
  ```

### Task 3.5 — Replace Inline Styles with CSS Classes
- [x] Audit `Dashboard.tsx` (~50 inline `style={{}}` occurrences)
- [x] Create CSS classes in `App.css` or `index.css` for common patterns
- [x] Replace inline styles in `Dashboard.tsx`, `ResearchHub.tsx`, `Backtest.tsx`

---

## Phase 4 — Agent Runner Hardening ⚡
**Estimated effort:** 2–3 hours  
**Priority:** MEDIUM-HIGH

### Task 4.1 — Add Binance Rate Limiting
- [x] In `cryptoswarms/adapters/binance_market_data.py`, add a simple semaphore-based rate limiter:
  ```python
  import asyncio
  _RATE_LIMITER = asyncio.Semaphore(10)  # max 10 concurrent requests
  
  async def _get(self, url, params=None):
      async with _RATE_LIMITER:
          # existing logic
  ```
- [x] Add retry logic with exponential backoff (3 retries, 1s → 2s → 4s)
- [x] Cache the `GET /api/v3/ticker/24hr` response for 30 seconds (it returns ALL symbols)

### Task 4.2 — Reduce Risk Event Write Frequency
- [x] In `agent_runner.py` `_risk_loop`, only write to DB when the risk level **changes**:
  ```python
  _last_risk_level = 0
  
  async def _risk_loop(self):
      while self._running:
          new_level = self._evaluate_risk()
          if new_level != self._last_risk_level:
              await self._db.write_risk_event(level=new_level, ...)
              self._last_risk_level = new_level
          await self._heartbeat.set_heartbeat("risk_monitor")
          await asyncio.sleep(self.RISK_INTERVAL)
  ```
- [x] This reduces writes from ~2,880/day to only when risk state actually transitions

### Task 4.3 — Add Signal Deduplication
- [x] Track a set of `(symbol, signal_type)` tuples already emitted this session
- [x] Only emit and write a signal if it hasn't been seen in the last N cycles (e.g., 5 cycles = 5 minutes):
  ```python
  _recent_signals: dict[tuple[str, str], int] = {}  # (symbol, type) -> cycle_count
  SIGNAL_COOLDOWN_CYCLES = 5
  ```
- [x] Decrement counters each cycle, only re-emit when cooldown expires

### Task 4.4 — Calibrate Confidence Values
- [x] Replace hardcoded confidence values with configurable constants:
  ```python
  # agent_runner.py — move to top or to a config dataclass
  BREAKOUT_BASE_CONFIDENCE = 0.78
  FUNDING_BASE_CONFIDENCE = 0.72
  SMART_MONEY_BASE_CONFIDENCE = 0.70
  ```
- [x] Add a `TODO` comment noting these should eventually come from backtested calibration curves

### Task 4.5 — Persist Signals History
- [x] Change `self._last_signals` from being overwritten each cycle to appending (with a maxlen):
  ```python
  from collections import deque
  self._signal_history: deque[dict] = deque(maxlen=200)
  
  # In _run_scan_cycle:
  self._signal_history.extend(signals)
  self._last_signals = signals  # still keep "latest cycle" for the API
  ```
- [x] Expose `signal_history` in `/api/agents/runner-status` response

---

## Phase 5 — Mock Data Cleanup 🎭
**Estimated effort:** 1–2 hours  
**Priority:** MEDIUM — prevents misleading dashboard data

### Task 5.1 — Fix `/api/backtest/results/{strategy_id}`
- [x] Option A: Remove the endpoint entirely and return 404 until real backtests are implemented
- [x] Option B: Keep it but clearly mark responses as synthetic:
  ```python
  return {
      "_synthetic": True,
      "_warning": "This data is generated for demo purposes. Not based on real backtests.",
      "strategy_id": strategy_id,
      ...
  }
  ```
- [x] Update frontend `Backtest.tsx` to display a banner when `_synthetic: true`

### Task 5.2 — Fix `/api/backtest/strategies`
- [x] When no real signals exist, return an empty list `[]` instead of a fake `AWAITING_SIGNALS` strategy
- [x] Update frontend to show "No strategies detected yet — start the scanner" message

### Task 5.3 — Fix Fallback Estimates in `/api/costs/daily`
- [x] The fallback cost estimate uses `scans * 0.0001` — add a comment explaining the math
- [x] Mark fallback data with `"_estimated": True` in the response
- [x] Frontend should display "(est.)" next to estimated values

---

## Phase 6 — Dependency & Configuration Cleanup 📦
**Estimated effort:** 1 hour  
**Priority:** MEDIUM

### Task 6.1 — Consolidate Dependency Files
- [x] Delete `requirements.txt` (only 2 entries, both already in `pyproject.toml`)
- [x] Delete `requirements_tui.txt` (for dead TUI code, removed in Phase 1)
- [x] `pyproject.toml` becomes the **single source of truth** for all dependencies
- [x] Add missing runtime dependencies to `pyproject.toml`:
  ```toml
  dependencies = [
      "fastapi>=0.111.1,<0.115.0",
      "pydantic>=2.7.0,<3.0.0",      # add upper bound
      "pydantic-settings>=2.0.0",      # add — used in api/settings.py
      "redis>=4.1.4,<5.0.0",
      "asyncpg>=0.29.0",
      "uvicorn>=0.29.0,<0.30.0",
      "httpx>=0.27.0",                 # add — used by BinanceMarketData
  ]
  ```

### Task 6.2 — Clean Up Docker Compose
- [x] Remove commented-out service blocks (qdrant, neo4j, sglang) or move to a `docker-compose.extras.yml`
- [x] Remove `qdrant_data` and `neo4j_data` volume declarations (not used if services are removed)
- [x] Update readiness check in `api/main.py` to only check active services:
  ```python
  # Remove qdrant_ok and sglang_ok from health check if not deployed
  checks = {
      "redis": redis_ok,
      "timescaledb": timescaledb_ok,
  }
  ```
- [x] Or: make the health check dynamically skip services marked as disabled in settings

### Task 6.3 — Update `.env.example`
- [x] Add `API_KEY=change-me-to-a-random-string`
- [x] Add `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- [x] Remove or comment out entries for disabled services (Neo4j, Qdrant, SGLang) with a note
- [x] Group entries by category with clear headers

### Task 6.4 — Convert Mission Control to Git Submodule
- [x] Remove `mission-control-upstream/` from the repo
- [x] Add as submodule: `git submodule add <upstream-url> mission-control-upstream`
- [x] Update `docker-compose.yml` build context if needed
- [x] Add submodule init to setup docs

---

## Phase 7 — Logging & Observability 📊
**Estimated effort:** 2 hours  
**Priority:** MEDIUM

### Task 7.1 — Replace `print()` with Structured Logging
- [x] In `api/main.py`: replace all `print(...)` calls with `logger.info(...)` / `logger.error(...)`
- [x] Configure logging format in `api/main.py` lifespan or a `logging_config.py`:
  ```python
  import logging
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
  )
  ```
- [ ] In `agent_runner.py`: already uses `logger` — good ✅
- [ ] In adapters: already uses `logger` — good ✅

### Task 7.2 — Stop Silently Swallowing Exceptions
- [x] Audit all `except Exception: pass` blocks (20+ locations)
- [x] Replace `pass` with at minimum `logger.debug("...", exc_info=True)`
- [x] For critical paths (DB writes, signal processing), use `logger.warning(...)`
- [x] Key files to audit:
  - [x] `api/main.py` — lines 97, 128, 152, 177, 202, 237, 264, 318, 366, 565
  - [x] `api/dashboard_repository.py` — lines 63, 86, 110, 134, 169, 194, 246, 292

### Task 7.3 — Add Request Logging Middleware
- [x] Create `api/middleware/logging.py`:
  ```python
  import time, logging
  from starlette.middleware.base import BaseHTTPMiddleware
  
  logger = logging.getLogger("api.access")
  
  class RequestLoggingMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request, call_next):
          start = time.monotonic()
          response = await call_next(request)
          duration_ms = (time.monotonic() - start) * 1000
          logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
          return response
  ```

---

## Phase 8 — Testing Improvements 🧪
**Estimated effort:** 3–4 hours  
**Priority:** MEDIUM

### Task 8.1 — Configure `pytest.ini` Properly
- [x] Expand `pytest.ini`:
  ```ini
  [pytest]
  asyncio_mode = auto
  testpaths = tests
  markers =
      integration: marks tests requiring live services
      slow: marks slow tests
  filterwarnings =
      ignore::DeprecationWarning
  ```

### Task 8.2 — Add API Integration Tests
- [x] Create `tests/integration/test_api_endpoints.py`
- [x] Use `httpx.AsyncClient` with FastAPI's `TestClient` to test actual route responses
- [x] Cover: health checks, dashboard overview, agents status, costs/budget
- [x] Mark with `@pytest.mark.integration`
- [x] Ensure tests work without live DB (mock the repository)

```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app

@pytest.mark.asyncio
async def test_health_live():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"
```

### Task 8.3 — Add Frontend Tests
- [x] Install Vitest: `npm install -D vitest @testing-library/react jsdom`
- [x] Add test script to `frontend/package.json`: `"test": "vitest run"`
- [x] Create `frontend/src/__tests__/App.test.tsx` — basic render test
- [x] Create `frontend/src/__tests__/config.test.ts` — verify API_URL config

### Task 8.4 — Add GitHub Actions CI
- [x] Create `.github/workflows/ci.yml`:
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    test-backend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -e ".[memory]" pytest
        - run: pytest -q --ignore=tests/integration
    
    test-frontend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-node@v4
          with:
            node-version: 22
        - run: cd frontend && npm ci && npm run build
    
    lint:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -e . ruff
        - run: ruff check cryptoswarms/ api/ agents/
  ```

---

## Phase 9 — Data Integrity & Schema 💾
**Estimated effort:** 1–2 hours  
**Priority:** MEDIUM

### Task 9.1 — Verify TimescaleDB Schema Exists
- [x] Check `data/schemas/` for SQL init scripts
- [x] Ensure all tables referenced in code exist in the schema:
  - [x] `signals` (agent_name, signal_type, symbol, confidence, acted_on, metadata, time)
  - [x] `regimes` (regime, confidence, indicators, time)
  - [x] `risk_events` (level, trigger, portfolio_heat, daily_dd, time)
  - [x] `trades` (id, strategy_id, mode, realised_pnl, slippage_bps, metadata, time)
  - [x] `validations` (strategy_id, gate, passed, time)
  - [x] `llm_costs` (agent, model, tokens_in, tokens_out, cost_usd, time)
- [x] Add `IF NOT EXISTS` to all `CREATE TABLE` statements

### Task 9.2 — Add Data Retention Policy
- [x] Add TimescaleDB `add_retention_policy` for high-frequency tables:
  ```sql
  SELECT add_retention_policy('risk_events', INTERVAL '30 days');
  SELECT add_retention_policy('signals', INTERVAL '90 days');
  ```
- [x] Prevents disk exhaustion from the risk event flood (Task 4.2) even if it's not yet fixed

### Task 9.3 — Add Connection Pooling in Dashboard Repository
- [x] Currently every query creates a new `asyncpg.connect()` → closes it
- [x] Switch to a shared connection pool:
  ```python
  class DashboardRepository:
      def __init__(self, registered_agents, dsn: str):
          self._dsn = dsn
          self._pool: asyncpg.Pool | None = None
      
      async def connect(self):
          self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
      
      async def _fetch(self, query, *args):
          async with self._pool.acquire() as conn:
              return await conn.fetch(query, *args)
  ```
- [x] Initialize pool in the FastAPI lifespan

---

## Phase 10 — Documentation Refresh 📝
**Estimated effort:** 1 hour  
**Priority:** LOW

### Task 10.1 — Update README.md
- [x] Remove references to TUI (`Moon Dev Quant App TUI`)
- [x] Update "Current status" to reflect actual state
- [x] Add section on the React frontend and how to run it
- [x] Add section on authentication setup
- [x] Update common commands to include frontend dev server

### Task 10.2 — Update SETUP_GUIDE.md
- [x] Add step for setting `API_KEY` in `.env`
- [x] Add step for `npm install` and `npm run dev` in `frontend/`
- [x] Remove TUI-related setup steps

### Task 10.3 — Create ARCHITECTURE.md
- [x] Move the Mermaid architecture diagram from the review into `docs/ARCHITECTURE.md`
- [x] Document the data flow: Binance → AgentRunner → TimescaleDB → API → Frontend
- [x] Document the decision flow: Signal → DecisionCouncil → Governor Gate → Execution

---

## Progress Tracker

| Phase | Tasks | Status | Estimated Time |
|---|---|---|---|
| **Phase 0** — Security | 5 tasks | 🟩 Completed | 2–3 hours |
| **Phase 1** — Dead Code | 5 tasks | 🟩 Completed | 30 min |
| **Phase 2** — API Split | 4 tasks | 🟩 Completed | 3–4 hours |
| **Phase 3** — Frontend | 5 tasks | 🟩 Completed | 2 hours |
| **Phase 4** — Agent Runner | 5 tasks | 🟩 Completed | 2–3 hours |
| **Phase 5** — Mock Data | 3 tasks | 🟩 Completed | 1–2 hours |
| **Phase 6** — Dependencies | 4 tasks | 🟩 Completed | 1 hour |
| **Phase 7** — Logging | 3 tasks | 🟩 Completed | 2 hours |
| **Phase 8** — Testing | 4 tasks | 🟩 Completed | 3–4 hours |
| **Phase 9** — Data | 3 tasks | 🟩 Completed | 1–2 hours |
| **Phase 10** — Docs | 3 tasks | 🟩 Completed | 1 hour |
| **Phase 11** — EV Foundation | 3 tasks | 🟩 Completed | 2–3 hours |
| **Phase 12** — Crypto Layer | 5 tasks | 🟩 Completed | 4–5 hours |
| **Phase 13** — Master Hub | 2 tasks | 🟩 Completed | 2 hours |
| **Phase 14** — Personas | 4 tasks | 🟩 Completed | 2 hours |
| **TOTAL** | **58 tasks** | | **~29–37 hours** |

---

## Phase 11 — EV Foundation (Decision Science)
**Priority:** HIGH (Strategic Edge)

### Task 11.1 — Core EV Calculator (Module 01)
- [x] Create `frontend/src/utils/probability.ts` with `calculateEV` logic.
- [x] Implement `frontend/src/views/ev/EvCalculator.tsx` with dynamic scenario rows.
- [x] Add live validation for probability sums (100%).

### Task 11.2 — Kelly Criterion Sizer (Module 02)
- [x] Implement `frontend/src/views/ev/KellySizer.tsx`.
- [x] Support Half/Quarter Kelly variants.
- [x] Add growth trajectory visualization (recharts).

### Task 11.3 — Bayesian Belief Updater (Module 03)
- [x] Implement `frontend/src/views/ev/BayesianUpdater.tsx`.
- [x] Support up to 10 sequential belief updates.

---

## Phase 12 — Crypto Trading Layer
**Priority:** MEDIUM-HIGH

### Task 12.1 — Asymmetric Trade Setup (Module C1)
- [x] Implement `frontend/src/views/ev/TradeSetup.tsx`.
- [x] Fee-adjusted EV and R:R scoring.

### Task 12.2 — Funding EV Analyzer (Module C2)
- [x] Implement `frontend/src/views/ev/FundingAnalyzer.tsx`.
- [x] Annualized yield and carry cost calculator.

### Task 12.3 — Liquidation Map & Cascade (Module C3)
- [x] Implement `frontend/src/views/ev/LiqMap.tsx`.
- [x] Visualization of magnet clusters and sweep zones.

### Task 12.4 — On-Chain Signal Aggregator (Module C4)
- [x] Implement `frontend/src/views/ev/OnChainSignals.tsx`.
- [x] Directional conviction scoring (CVD/OI/Whale).

### Task 12.5 — Backtest EV Validator (Module C7)
- [x] Implement `frontend/src/views/ev/BacktestValidator.tsx`.
- [x] Monte Carlo permutation significance testing.

---

## Phase 13 — Master Hub & Calibration
**Priority:** STRATEGIC

### Task 13.1 — Master Dashboard (Module C8)
- [x] Implement `frontend/src/views/ev/MasterDashboard.tsx`.
- [x] Unified pre-trade GO / NO GO verdict system.

### Task 13.2 — Calibration Tracker (Module 08)
- [x] Implement `frontend/src/views/ev/CalibrationTracker.tsx`.
- [x] Track win-rate accuracy over time.

---

## Phase 14 — Agent Personas (Behavioral Souls)
**Objective:** Encode Phase 11-13 math into distinct agent behaviors and debate personalities.
**Priority:** MEDIUM-HIGH (Strategic Quality)

### Task 14.1 — Architectural Definition
- [x] Create `docs/AGENT_PERSONAS.md` defining Probability Architect, Microstructure Oracle, and Calibration Governor.

### Task 14.2 — Probability Architect Implementation
- [x] Implement `ProbabilitySolver` in `agents/orchestration/decision_council.py`.
- [x] Anchor logic to EV ($5 hurdle) and Bayesian Posterior.

### Task 14.3 — Microstructure Oracle Implementation
- [x] Implement `MicrostructureSolver` in `agents/orchestration/decision_council.py`.
- [x] Anchor weight to positioning and institutional gates.

### Task 14.4 — Calibration Governor Implementation
- [x] Implement `CalibrationSolver` in `agents/orchestration/decision_council.py`.
- [x] Anchor logic to meta-readiness and attribution drift.


> [!IMPORTANT]
> **Recommended execution order:** Phase 0 → Phase 1 → Phase 6 → Phase 2 → Phase 4 → Phase 5 → Phase 3 → Phase 11 → Phase 12 → Phase 13 → Phase 7 → Phase 8 → Phase 9 → Phase 10
>
> Start with security (Phase 0) and dead code cleanup (Phase 1) — they're fast wins that immediately improve the project quality. Then tackle the API split (Phase 2) since everything else depends on a clean API layer.

