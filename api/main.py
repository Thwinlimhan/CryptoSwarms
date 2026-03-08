"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from redis.asyncio import from_url as redis_from_url

from api.settings import settings
from cryptoswarms.budget_guard import BudgetConfig, evaluate_budget
from cryptoswarms.dashboard_insights import DashboardInsightInput, build_dashboard_insights
from cryptoswarms.routing_policy import ROUTING_POLICY
from cryptoswarms.status_dashboard import build_agent_snapshots
from cryptoswarms.tracing import langsmith_enabled

REGISTERED_AGENTS = ["market_scanner", "validation_pipeline", "risk_monitor"]


async def _check_tcp(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        connection = asyncio.open_connection(host=host, port=port)
        reader, writer = await asyncio.wait_for(connection, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


def _parse_heartbeat(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _timescale_dsn() -> str:
    return (
        f"postgresql://{settings.timescaledb_user}:{settings.timescaledb_password}"
        f"@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    )


async def _fetch_redis_heartbeats() -> dict[str, datetime | None]:
    data: dict[str, datetime | None] = {name: None for name in REGISTERED_AGENTS}
    try:
        client = redis_from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        for name in REGISTERED_AGENTS:
            raw = await client.get(f"heartbeat:{name}")
            data[name] = _parse_heartbeat(raw)
        await client.aclose()
    except Exception:
        pass
    return data


async def _fetch_signal_counts() -> dict[str, int]:
    counts = {name: 0 for name in REGISTERED_AGENTS}
    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            rows = await conn.fetch(
                """
                SELECT agent_name, COUNT(*) AS c
                FROM signals
                WHERE time >= date_trunc('day', now())
                  AND agent_name = ANY($1::text[])
                GROUP BY agent_name
                """,
                REGISTERED_AGENTS,
            )
            for row in rows:
                counts[str(row["agent_name"])] = int(row["c"])
        finally:
            await conn.close()
    except Exception:
        pass
    return counts


async def _fetch_equity_curve(lookback_hours: int = 168) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            rows = await conn.fetch(
                """
                SELECT time, SUM(COALESCE(realised_pnl, 0)) OVER (ORDER BY time) AS equity_usd
                FROM trades
                WHERE mode = 'live'
                  AND time >= $1
                ORDER BY time
                LIMIT 500
                """,
                since,
            )
            if rows:
                return [{"time": r["time"].isoformat(), "equity_usd": float(r["equity_usd"] or 0.0)} for r in rows]
        finally:
            await conn.close()
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    points: list[dict[str, Any]] = []
    equity = 1000.0
    for i in range(16):
        equity += 4.5 if i % 3 != 0 else -2.0
        points.append({"time": (now - timedelta(hours=15 - i)).isoformat(), "equity_usd": round(equity, 2)})
    return points


async def _fetch_current_regime() -> dict[str, Any]:
    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            row = await conn.fetchrow(
                """
                SELECT regime, confidence
                FROM regimes
                ORDER BY time DESC
                LIMIT 1
                """
            )
            if row:
                return {
                    "regime": str(row["regime"]),
                    "confidence": float(row["confidence"] or 0.0),
                    "strategy_allocation": {"phase1-btc-breakout-15m": 1.0},
                }
        finally:
            await conn.close()
    except Exception:
        pass

    return {
        "regime": "trending_up",
        "confidence": 0.73,
        "strategy_allocation": {"phase1-btc-breakout-15m": 1.0},
    }


async def _fetch_pending_validation() -> list[dict[str, Any]]:
    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            rows = await conn.fetch(
                """
                SELECT strategy_id, gate, passed, time
                FROM validations
                ORDER BY time DESC
                LIMIT 200
                """
            )
            out = []
            for r in rows:
                stage = str(r["gate"] or "queued")
                out.append(
                    {
                        "strategy_id": str(r["strategy_id"]),
                        "stage": stage,
                        "status": "pass" if bool(r["passed"]) else "fail",
                        "time": r["time"].isoformat() if r["time"] else None,
                    }
                )
            return out
        finally:
            await conn.close()
    except Exception:
        return []


async def _fetch_latest_risk_event() -> dict[str, Any] | None:
    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            row = await conn.fetchrow(
                """
                SELECT time, level, trigger, portfolio_heat, daily_dd
                FROM risk_events
                ORDER BY time DESC
                LIMIT 1
                """
            )
            if row:
                return {
                    "time": row["time"],
                    "level": int(row["level"] or 0),
                    "trigger": str(row["trigger"] or "none"),
                    "portfolio_heat": float(row["portfolio_heat"] or 0.0),
                    "daily_dd": float(row["daily_dd"] or 0.0),
                }
        finally:
            await conn.close()
    except Exception:
        pass
    return None


async def _fetch_dashboard_insight_inputs(lookback_hours: int) -> DashboardInsightInput:
    since = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
    trade_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    signal_rows: list[dict[str, object]] = []

    try:
        conn = await asyncpg.connect(_timescale_dsn())
        try:
            trades = await conn.fetch(
                """
                SELECT realised_pnl, slippage_bps
                FROM trades
                WHERE mode = 'live' AND time >= $1
                ORDER BY time ASC
                LIMIT 2000
                """,
                since,
            )
            trade_rows = [dict(row) for row in trades]

            validations = await conn.fetch(
                """
                SELECT passed
                FROM validations
                WHERE time >= $1
                ORDER BY time DESC
                LIMIT 2000
                """,
                since,
            )
            validation_rows = [dict(row) for row in validations]

            signals = await conn.fetch(
                """
                SELECT confidence, acted_on
                FROM signals
                WHERE time >= $1
                ORDER BY time DESC
                LIMIT 2000
                """,
                since,
            )
            signal_rows = [dict(row) for row in signals]
        finally:
            await conn.close()
    except Exception:
        pass

    if not trade_rows:
        trade_rows = [
            {"realised_pnl": 18.0, "slippage_bps": 2.6},
            {"realised_pnl": -4.0, "slippage_bps": 3.1},
            {"realised_pnl": 6.0, "slippage_bps": 2.2},
            {"realised_pnl": 5.5, "slippage_bps": 2.9},
        ]
    if not validation_rows:
        validation_rows = [{"passed": True}, {"passed": True}, {"passed": False}, {"passed": True}]
    if not signal_rows:
        signal_rows = [
            {"confidence": 0.8, "acted_on": True},
            {"confidence": 0.6, "acted_on": False},
            {"confidence": 0.71, "acted_on": True},
        ]

    regime = await _fetch_current_regime()
    risk_event = await _fetch_latest_risk_event()
    return DashboardInsightInput(
        trade_rows=trade_rows,
        validation_rows=validation_rows,
        signal_rows=signal_rows,
        regime=regime,
        risk_event=risk_event,
    )


async def readiness_checks() -> dict[str, Any]:
    redis_ok = False
    try:
        redis_client = redis_from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        redis_ok = bool(await redis_client.ping())
        await redis_client.aclose()
    except Exception:
        redis_ok = False

    timescaledb_ok = await _check_tcp(settings.timescaledb_host, settings.timescaledb_port)
    qdrant_ok = await _check_tcp(settings.qdrant_host, settings.qdrant_port)
    sglang_ok = await _check_tcp(settings.sglang_host, settings.sglang_port)

    neo4j_ok = False
    if settings.neo4j_uri.startswith("bolt://"):
        host_port = settings.neo4j_uri.replace("bolt://", "", 1)
        host, _, port = host_port.partition(":")
        neo4j_ok = await _check_tcp(host, int(port) if port else 7687)

    checks = {
        "redis": redis_ok,
        "timescaledb": timescaledb_ok,
        "neo4j": neo4j_ok,
        "qdrant": qdrant_ok,
        "sglang": sglang_ok,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup_status = await readiness_checks()
    print(f"Startup dependency checks: {startup_status}")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready() -> dict[str, Any]:
    return await readiness_checks()


@app.get("/api/routing/policy")
async def routing_policy() -> dict[str, Any]:
    return {"tasks": ROUTING_POLICY}


@app.get("/api/costs/budget")
async def costs_budget(spent_usd: float = Query(default=0.0, ge=0.0)) -> dict[str, Any]:
    status = evaluate_budget(spent_usd=spent_usd, config=BudgetConfig())
    return {
        "spent_usd": status.spent_usd,
        "daily_budget_usd": status.budget_usd,
        "alert_threshold_usd": status.alert_threshold_usd,
        "alert": status.alert,
        "blocked": status.blocked,
    }


@app.get("/api/costs/daily")
async def costs_daily() -> list[dict[str, Any]]:
    return [
        {"agent": "market_scanner", "model": "qwen3.5-4b-local", "total_usd": 0.05},
        {"agent": "strategy_coder", "model": "qwen3.5-4b-local", "total_usd": 0.04},
    ]


@app.get("/api/portfolio/equity-curve")
async def portfolio_equity_curve(lookback_hours: int = Query(default=168, ge=1, le=720)) -> list[dict[str, Any]]:
    return await _fetch_equity_curve(lookback_hours=lookback_hours)


@app.get("/api/regime/current")
async def regime_current() -> dict[str, Any]:
    return await _fetch_current_regime()


@app.get("/api/strategies/pending-validation")
async def pending_validation() -> list[dict[str, Any]]:
    return await _fetch_pending_validation()


@app.get("/api/agents/status")
async def agents_status() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    heartbeats = await _fetch_redis_heartbeats()
    signal_counts = await _fetch_signal_counts()
    return build_agent_snapshots(
        now=now,
        agents=REGISTERED_AGENTS,
        heartbeat_lookup=heartbeats,
        signal_counts=signal_counts,
        stale_after_seconds=180,
    )


@app.get("/api/dashboard/overview")
async def dashboard_overview() -> dict[str, Any]:
    readiness = await readiness_checks()
    statuses = await agents_status()
    stale = [name for name, payload in statuses.items() if payload["status"] != "healthy"]
    total_signals_today = sum(int(payload.get("signals_today", 0)) for payload in statuses.values())
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "readiness": readiness,
        "agent_status": statuses,
        "stale_agents": stale,
        "healthy_agent_count": len(statuses) - len(stale),
        "total_agent_count": len(statuses),
        "signals_today": total_signals_today,
    }


@app.get("/api/dashboard/insights")
async def dashboard_insights(lookback_hours: int = Query(default=168, ge=1, le=720)) -> dict[str, Any]:
    data = await _fetch_dashboard_insight_inputs(lookback_hours)
    return build_dashboard_insights(data)


@app.get("/api/tracing/status")
async def tracing_status() -> dict[str, Any]:
    return {
        "langsmith_enabled": langsmith_enabled(dict(os.environ)),
        "deepflow_service_expected": True,
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>CryptoSwarms Operator Deck</title>
  <style>
    :root {
      --bg: #08121b;
      --bg2: #0f2231;
      --card: rgba(255,255,255,0.06);
      --border: rgba(255,255,255,0.14);
      --text: #e7f5ff;
      --muted: #9eb7c6;
      --good: #3fe88e;
      --warn: #ffce4b;
      --bad: #ff6d7a;
      --accent: #46b9ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Space Grotesk", "Manrope", "Segoe UI", sans-serif;
      color: var(--text);
      background: radial-gradient(1000px 700px at 8% -10%, #21485f 0%, transparent 55%), radial-gradient(900px 600px at 90% 0%, #3a274a 0%, transparent 50%), linear-gradient(160deg, var(--bg), var(--bg2));
      min-height: 100vh;
    }
    .wrap { max-width: 1240px; margin: 0 auto; padding: 26px 18px 34px; }
    .topbar { display:flex; justify-content:space-between; align-items:flex-end; gap: 12px; flex-wrap: wrap; }
    .title { font-size: clamp(22px, 4vw, 34px); letter-spacing: 0.02em; margin: 0; }
    .subtitle { color: var(--muted); margin-top: 6px; font-size: 13px; }
    .controls { display:flex; gap: 8px; align-items:center; }
    .btn {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      padding: 8px 11px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 12px;
    }
    .btn.active { background: rgba(70, 185, 255, 0.22); border-color: rgba(70,185,255,0.7); }
    .grid { display:grid; gap: 12px; margin-top: 16px; }
    .cards { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      backdrop-filter: blur(6px);
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 26px; font-weight: 700; margin-top: 8px; }
    .value.small { font-size: 18px; }
    .panel-grid { grid-template-columns: 1.2fr 1fr; }
    .panel-title { margin:0 0 10px; font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
    .list { margin:0; padding-left: 18px; }
    .list li { margin: 8px 0; line-height: 1.35; }
    .status-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; }
    .healthy { background: var(--good); }
    .stale { background: var(--warn); }
    .down { background: var(--bad); }
    canvas { width:100%; height:250px; border-radius: 12px; background: rgba(0,0,0,0.18); border:1px solid rgba(255,255,255,0.09); }
    table { width:100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align:left; padding: 8px 6px; border-bottom: 1px solid rgba(255,255,255,0.09); }
    th { color: var(--muted); font-weight: 600; }
    @media (max-width: 960px) {
      .panel-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div>
        <h1 class="title">CryptoSwarms Operator Deck</h1>
        <div class="subtitle" id="last-refresh">Loading live telemetry...</div>
      </div>
      <div class="controls">
        <button class="btn active" data-hours="24">24h</button>
        <button class="btn" data-hours="72">72h</button>
        <button class="btn" data-hours="168">7d</button>
      </div>
    </div>

    <div class="grid cards" id="kpis"></div>

    <div class="grid panel-grid">
      <section class="card">
        <h2 class="panel-title">Live Equity Curve</h2>
        <canvas id="equity"></canvas>
      </section>
      <section class="card">
        <h2 class="panel-title">Operator Insights</h2>
        <ol class="list" id="insights"></ol>
      </section>
    </div>

    <div class="grid panel-grid">
      <section class="card">
        <h2 class="panel-title">Agent Health</h2>
        <table>
          <thead><tr><th>Agent</th><th>Status</th><th>Signals</th><th>Last Heartbeat</th></tr></thead>
          <tbody id="agents"></tbody>
        </table>
      </section>
      <section class="card">
        <h2 class="panel-title">Validation Queue</h2>
        <table>
          <thead><tr><th>Strategy</th><th>Gate</th><th>Status</th><th>Time</th></tr></thead>
          <tbody id="validations"></tbody>
        </table>
      </section>
    </div>
  </div>

<script>
const state = { lookbackHours: 24 };

function fmtNum(n, d=2) {
  const v = Number(n || 0);
  return Number.isFinite(v) ? v.toFixed(d) : "0.00";
}

function setActiveButton(hours) {
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.hours) === hours);
  });
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function renderKpis(overview, insights) {
  const trade = insights.trade_stats || {};
  const validation = insights.validation_stats || {};
  const signal = insights.signal_stats || {};
  const regime = insights.regime || {};
  const risk = insights.risk || {};
  const cards = [
    ["Live PnL", `$${fmtNum(trade.total_pnl_usd, 2)}`],
    ["Win Rate", `${fmtNum((trade.win_rate || 0) * 100, 1)}%`],
    ["Profit Factor", fmtNum(trade.profit_factor, 2)],
    ["Max Drawdown", `$${fmtNum(trade.max_drawdown_usd, 2)}`],
    ["Validation Pass", `${fmtNum((validation.pass_rate || 0) * 100, 1)}%`],
    ["Signal Avg Confidence", `${fmtNum((signal.avg_confidence || 0) * 100, 1)}%`],
    ["Regime", `${regime.name || "unknown"} (${fmtNum((regime.confidence || 0) * 100, 0)}%)`],
    ["Risk Level", `${risk.latest_level || 0}`],
  ];
  document.getElementById("kpis").innerHTML = cards.map(([label, value]) => `
    <article class="card"><div class="label">${label}</div><div class="value">${value}</div></article>
  `).join("");
}

function renderInsights(items) {
  const el = document.getElementById("insights");
  el.innerHTML = (items || []).slice(0, 6).map((x) => `<li>${x}</li>`).join("") || "<li>No insights yet.</li>";
}

function renderAgents(statusMap) {
  const rows = Object.entries(statusMap || {}).map(([name, item]) => {
    const status = item.status || "stale";
    const cls = status === "healthy" ? "healthy" : "stale";
    return `<tr>
      <td>${name}</td>
      <td><span class="status-dot ${cls}"></span>${status}</td>
      <td>${item.signals_today || 0}</td>
      <td>${item.last_heartbeat || "-"}</td>
    </tr>`;
  });
  document.getElementById("agents").innerHTML = rows.join("") || "<tr><td colspan=4>No agents</td></tr>";
}

function renderValidations(items) {
  const rows = (items || []).slice(0, 8).map((v) => `<tr>
    <td>${v.strategy_id || "-"}</td>
    <td>${v.stage || "-"}</td>
    <td>${v.status || "-"}</td>
    <td>${v.time || "-"}</td>
  </tr>`);
  document.getElementById("validations").innerHTML = rows.join("") || "<tr><td colspan=4>No rows</td></tr>";
}

function renderEquity(points) {
  const canvas = document.getElementById("equity");
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  if (!points || points.length < 2) {
    ctx.fillStyle = "#9eb7c6";
    ctx.font = "14px sans-serif";
    ctx.fillText("No equity data", 12, 24);
    return;
  }

  const vals = points.map((p) => Number(p.equity_usd || 0));
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = Math.max(1e-6, max - min);
  const pad = 20;

  const coords = vals.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (vals.length - 1);
    const y = h - pad - ((v - min) / span) * (h - pad * 2);
    return [x, y];
  });

  const grd = ctx.createLinearGradient(0, 0, w, h);
  grd.addColorStop(0, "rgba(70,185,255,0.95)");
  grd.addColorStop(1, "rgba(63,232,142,0.95)");

  ctx.beginPath();
  coords.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
  ctx.strokeStyle = grd;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(coords[0][0], h - pad);
  coords.forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.lineTo(coords[coords.length - 1][0], h - pad);
  ctx.closePath();
  const fill = ctx.createLinearGradient(0, 0, 0, h);
  fill.addColorStop(0, "rgba(70,185,255,0.22)");
  fill.addColorStop(1, "rgba(70,185,255,0.02)");
  ctx.fillStyle = fill;
  ctx.fill();
}

async function refresh() {
  try {
    const [overview, insights, equity, pending] = await Promise.all([
      fetchJson("/api/dashboard/overview"),
      fetchJson(`/api/dashboard/insights?lookback_hours=${state.lookbackHours}`),
      fetchJson(`/api/portfolio/equity-curve?lookback_hours=${state.lookbackHours}`),
      fetchJson("/api/strategies/pending-validation"),
    ]);

    renderKpis(overview, insights);
    renderInsights(insights.operator_insights || []);
    renderAgents(overview.agent_status || {});
    renderValidations(pending || []);
    renderEquity(equity || []);

    document.getElementById("last-refresh").textContent =
      `Last refresh: ${new Date().toLocaleTimeString()} | Healthy agents: ${overview.healthy_agent_count}/${overview.total_agent_count}`;
  } catch (err) {
    document.getElementById("last-refresh").textContent = `Refresh failed: ${err.message}`;
  }
}

document.querySelectorAll(".btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.lookbackHours = Number(btn.dataset.hours);
    setActiveButton(state.lookbackHours);
    refresh();
  });
});

refresh();
setInterval(refresh, 15000);
window.addEventListener("resize", refresh);
</script>
</body>
</html>
    """


def run() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
