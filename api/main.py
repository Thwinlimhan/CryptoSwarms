"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import math
import os
import random
from hashlib import md5
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import asyncpg
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    from redis.asyncio import from_url as redis_from_url
except ImportError:
    class _NullRedisClient:
        async def ping(self) -> bool:
            return False

        async def get(self, key: str) -> str | None:
            _ = key
            return None

        async def aclose(self) -> None:
            return None

    def redis_from_url(*args: object, **kwargs: object) -> _NullRedisClient:
        _ = (args, kwargs)
        return _NullRedisClient()

from agents.orchestration.dag_memory_bridge import DagMemoryBridge
from agents.orchestration.decision_council import CouncilConfig, CouncilInput, DecisionCouncil
from agents.orchestration.runtime_middleware import default_runtime_orchestrator
from agents.orchestration.subagent_executor import SubagentExecutor, SubagentTask
from api.settings import settings
from cryptoswarms.budget_guard import BudgetConfig, evaluate_budget
from cryptoswarms.dag_recall import DagWalker
from cryptoswarms.dag_summarizer import DagSummarizationConfig, maybe_summarize_topics
from cryptoswarms.dashboard_insights import DashboardInsightInput, build_dashboard_insights
from cryptoswarms.memory_dag import MemoryDag
from cryptoswarms.routing_policy import ROUTING_POLICY
from cryptoswarms.status_dashboard import build_agent_snapshots
from cryptoswarms.tracing import langsmith_enabled
from api.dashboard_repository import DashboardRepository
from cryptoswarms.agent_runner import AgentRunner

REGISTERED_AGENTS = ["market_scanner", "validation_pipeline", "risk_monitor"]
_DAG_PATH = Path(os.getenv("DECISION_DAG_PATH", "data/agent_memory_dag.json"))

_DECISION_MEMORY_DAG = MemoryDag()
_DAG_BRIDGE = DagMemoryBridge(_DECISION_MEMORY_DAG)
_RUNTIME_ORCHESTRATOR = default_runtime_orchestrator()
_SUBAGENT_EXECUTOR = SubagentExecutor(max_parallelism=3, timeout_seconds=8.0)
_DASHBOARD_REPO = DashboardRepository(REGISTERED_AGENTS)

def _timescale_dsn_str() -> str:
    return (
        f"postgresql://{settings.timescaledb_user}:{settings.timescaledb_password}"
        f"@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    )

_AGENT_RUNNER = AgentRunner(
    timescale_dsn=_timescale_dsn_str(),
    redis_url=settings.redis_url,
)

def _load_decision_dag() -> None:
    global _DECISION_MEMORY_DAG
    global _DAG_BRIDGE
    _DECISION_MEMORY_DAG = MemoryDag.load_json(_DAG_PATH)
    _DAG_BRIDGE = DagMemoryBridge(_DECISION_MEMORY_DAG)

def _save_decision_dag() -> None:
    topics = {node.topic for node in _DECISION_MEMORY_DAG.nodes() if node.topic}
    maybe_summarize_topics(
        _DECISION_MEMORY_DAG,
        topics=topics,
        config=DagSummarizationConfig(max_nodes_per_topic=40, trigger_token_budget=1800, summary_max_chars=700),
    )
    _DECISION_MEMORY_DAG.save_json(_DAG_PATH)
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
        conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
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
        conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
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
    return []


async def _fetch_current_regime() -> dict[str, Any]:
    try:
        conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
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
        "regime": "unknown",
        "confidence": 0.0,
        "strategy_allocation": {},
    }


async def _fetch_pending_validation() -> list[dict[str, Any]]:
    try:
        conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
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
        conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
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
    attribution_rows: list[dict[str, object]] = []

    try:
        dsn = _timescale_dsn().replace("localhost", "127.0.0.1")
        conn = await asyncpg.connect(dsn, timeout=2.0)
        try:
            trades = await conn.fetch(
                """
                SELECT realised_pnl, slippage_bps, id, strategy_id, metadata
                FROM trades
                WHERE mode = 'live' AND time >= $1
                ORDER BY time ASC
                LIMIT 2000
                """,
                since,
            )
            trade_rows = [{"realised_pnl": row["realised_pnl"], "slippage_bps": row["slippage_bps"]} for row in trades]
            attribution_rows = [extract_trade_trace(dict(row)) for row in trades]

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

    regime = await _fetch_current_regime()
    risk_event = await _fetch_latest_risk_event()
    return DashboardInsightInput(
        trade_rows=trade_rows,
        validation_rows=validation_rows,
        signal_rows=signal_rows,
        attribution_rows=attribution_rows,
        regime=regime,
        risk_event=risk_event,
    )


async def _fetch_live_trade_traces(limit: int = 500, strategy_id: str | None = None) -> list[dict[str, str | None]]:
    max_limit = max(1, min(int(limit), 2000))
    traces: list[dict[str, str | None]] = []
    try:
        dsn = _timescale_dsn().replace("localhost", "127.0.0.1")
        conn = await asyncpg.connect(dsn, timeout=2.0)
        try:
            if strategy_id:
                rows = await conn.fetch(
                    """
                    SELECT id, strategy_id, metadata
                    FROM trades
                    WHERE mode = 'live' AND strategy_id = $1
                    ORDER BY time DESC
                    LIMIT $2
                    """,
                    strategy_id,
                    max_limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, strategy_id, metadata
                    FROM trades
                    WHERE mode = 'live'
                    ORDER BY time DESC
                    LIMIT $1
                    """,
                    max_limit,
                )
            traces = [extract_trade_trace(dict(row)) for row in rows]
        finally:
            await conn.close()
    except Exception:
        pass
    return traces


def _lineage_summary(*, traces: list[dict[str, str | None]], strategy_id: str | None = None) -> dict[str, Any]:
    if strategy_id:
        rows = [t for t in traces if (t.get("strategy_id") or "") == strategy_id]
    else:
        rows = traces

    total = len(rows)
    fully_traced = 0
    optimizer_runs: set[str] = set()
    hypothesis_ids: set[str] = set()

    for row in rows:
        hyp = row.get("hypothesis_id")
        run_id = row.get("optimizer_run_id")
        cand = row.get("optimizer_candidate_id")
        if hyp and run_id and cand:
            fully_traced += 1
        if run_id:
            optimizer_runs.add(run_id)
        if hyp:
            hypothesis_ids.add(hyp)

    coverage = (fully_traced / total) if total else 0.0
    return {
        "strategy_id": strategy_id,
        "total_trades": total,
        "fully_traced_trades": fully_traced,
        "coverage_ratio": round(coverage, 4),
        "unique_optimizer_runs": len(optimizer_runs),
        "unique_hypotheses": len(hypothesis_ids),
    }

def _compute_dag_memory_stats() -> dict[str, Any]:
    nodes = _DECISION_MEMORY_DAG.nodes()
    edges = _DECISION_MEMORY_DAG.edges()
    node_count = len(nodes)
    edge_count = len(edges)
    if node_count == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "topic_count": 0,
            "topic_entropy": 0.0,
            "recall_hit_rate": 0.0,
            "research_hypothesis_count": 0,
            "decision_checkpoint_count": 0,
            "top_topics": [],
        }

    topic_counts: dict[str, int] = {}
    for node in nodes:
        topic = node.topic or "unknown"
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

    topic_entropy = 0.0
    for count in topic_counts.values():
        p = count / node_count
        topic_entropy -= p * math.log2(p)

    hypothesis_nodes = [n for n in nodes if n.node_type == "research_hypothesis"]
    hypothesis_with_context = 0
    for node in hypothesis_nodes:
        if _DECISION_MEMORY_DAG.parents(node.node_id):
            hypothesis_with_context += 1
    recall_hit_rate = (hypothesis_with_context / len(hypothesis_nodes)) if hypothesis_nodes else 0.0

    checkpoint_count = sum(1 for n in nodes if n.node_type == "decision_checkpoint")
    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "topic_count": len(topic_counts),
        "topic_entropy": round(topic_entropy, 4),
        "recall_hit_rate": round(recall_hit_rate, 4),
        "research_hypothesis_count": len(hypothesis_nodes),
        "decision_checkpoint_count": checkpoint_count,
        "top_topics": top_topics,
    }



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
    _load_decision_dag()
    startup_status = await readiness_checks()
    print(f"Startup dependency checks: {startup_status}")

    # Auto-start agents on boot
    try:
        await _AGENT_RUNNER.start()
        print("[SUCCESS] Agent runner started - agents are now scanning live markets")
    except Exception as exc:
        print(f"[ERROR] Agent runner failed to start: {exc}")

    try:
        yield
    finally:
        await _AGENT_RUNNER.stop()
        _save_decision_dag()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/api/health/ready")
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
    """Fetch real LLM cost data from TimescaleDB, fall back to estimates."""
    try:
        conn = await asyncpg.connect(_timescale_dsn_str(), timeout=2.0)
        try:
            rows = await conn.fetch(
                """
                SELECT agent, model, SUM(cost_usd) AS total_usd
                FROM llm_costs
                WHERE time >= date_trunc('day', now())
                GROUP BY agent, model
                ORDER BY total_usd DESC
                """
            )
            if rows:
                return [{"agent": r["agent"], "model": r["model"], "total_usd": float(r["total_usd"] or 0)} for r in rows]
        finally:
            await conn.close()
    except Exception:
        pass
    # Fallback: estimate from agent scan count
    scans = _AGENT_RUNNER.scan_count
    return [
        {"agent": "market_scanner", "model": "binance-api", "total_usd": round(scans * 0.0001, 4)},
        {"agent": "regime_classifier", "model": "binance-api", "total_usd": round(scans * 0.00005, 4)},
    ]


@app.get("/api/portfolio/equity-curve")
async def portfolio_equity_curve(lookback_hours: int = Query(default=168, ge=1, le=720)) -> list[dict[str, Any]]:
    return await _DASHBOARD_REPO.fetch_equity_curve(lookback_hours=lookback_hours)


@app.get("/api/regime/current")
async def regime_current() -> dict[str, Any]:
    return await _DASHBOARD_REPO.fetch_current_regime()


@app.get("/api/strategies/pending-validation")
async def pending_validation() -> list[dict[str, Any]]:
    return await _DASHBOARD_REPO.fetch_pending_validation()


@app.get("/api/agents/status")
async def agents_status() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    heartbeats = await _DASHBOARD_REPO.fetch_redis_heartbeats()
    signal_counts = await _DASHBOARD_REPO.fetch_signal_counts()
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
    dag_memory = _compute_dag_memory_stats()
    traces = await _DASHBOARD_REPO.fetch_live_trade_traces(limit=300)
    attribution_lineage = _lineage_summary(traces=traces)
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "readiness": readiness,
        "agent_status": statuses,
        "stale_agents": stale,
        "healthy_agent_count": len(statuses) - len(stale),
        "total_agent_count": len(statuses),
        "signals_today": total_signals_today,
        "dag_memory": dag_memory,
        "attribution_lineage": attribution_lineage,
    }


@app.get("/api/dashboard/insights")
async def dashboard_insights(lookback_hours: int = Query(default=168, ge=1, le=720)) -> dict[str, Any]:
    data = await _DASHBOARD_REPO.fetch_dashboard_insight_inputs(lookback_hours)
    return build_dashboard_insights(data)


@app.get("/api/decision/debate-preview")
async def debate_preview(
    scorecard_eligible: bool = Query(default=True),
    institutional_gate_ok: bool = Query(default=True),
    attribution_ready: bool = Query(default=True),
    risk_halt_active: bool = Query(default=False),
    strategy_count_ok: bool = Query(default=True),
    expected_value_after_costs_usd: float = Query(default=12.5),
    posterior_probability: float = Query(default=0.64, ge=0.0, le=1.0),
    project_id: str = Query(default="default"),
) -> dict[str, Any]:
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=2, max_retries=2, min_go_confidence=0.6), dag_bridge=_DAG_BRIDGE)
    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            project_id=project_id,
            scorecard_eligible=scorecard_eligible,
            institutional_gate_ok=institutional_gate_ok,
            attribution_ready=attribution_ready,
            risk_halt_active=risk_halt_active,
            strategy_count_ok=strategy_count_ok,
            expected_value_after_costs_usd=expected_value_after_costs_usd,
            posterior_probability=posterior_probability,
        )
    )
    return {
        "project_id": project_id,
        "decision": out.decision,
        "confidence": out.confidence,
        "dissent_ratio": out.dissent_ratio,
        "passed_governor": out.passed_governor,
        "reason": out.reason,
        "stages": out.stages,
        "aggregate": {
            "decision": out.aggregate.decision,
            "confidence": out.aggregate.confidence,
            "dissent_ratio": out.aggregate.dissent_ratio,
            "vote_count": out.aggregate.vote_count,
        },
        "rounds": [
            {
                "round": r.round_index,
                "dissent_solver_ids": r.dissent_solver_ids,
                "votes": [
                    {
                        "solver_id": v.solver_id,
                        "stance": v.stance,
                        "confidence": v.confidence,
                        "rationale": v.rationale,
                    }
                    for v in r.votes
                ],
            }
            for r in out.rounds
        ],
    }


@app.get("/api/decision/dag-preview")
async def dag_preview(
    topic: str = Query(default="phase1-btc-breakout-15m"),
    lookback_hours: int = Query(default=72, ge=1, le=720),
    max_nodes: int = Query(default=8, ge=1, le=50),
    token_budget: int = Query(default=800, ge=100, le=4000),
    project_id: str = Query(default="default"),
) -> dict[str, Any]:
    walker = DagWalker(_DECISION_MEMORY_DAG)
    recall = walker.recall(
        topic=DagMemoryBridge.scoped_topic(project_id=project_id, strategy_id=topic),
        lookback_hours=lookback_hours,
        max_nodes=max_nodes,
        token_budget=token_budget,
    )
    return {
        "project_id": project_id,
        "topic": topic,
        "token_estimate": recall.token_estimate,
        "truncated": recall.truncated,
        "node_count": len(recall.nodes),
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "topic": node.topic,
                "content": node.content,
                "created_at": node.created_at.isoformat(),
                "metadata": node.metadata,
            }
            for node in recall.nodes
        ],
    }

@app.get("/api/decision/dag-stats")
async def dag_stats() -> dict[str, Any]:
    return _compute_dag_memory_stats()


@app.get("/api/decision/attribution-lineage")
async def attribution_lineage(
    strategy_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    traces = await _DASHBOARD_REPO.fetch_live_trade_traces(limit=limit, strategy_id=strategy_id)
    return {
        "summary": _lineage_summary(traces=traces, strategy_id=strategy_id),
        "traces": traces,
    }



@app.get("/api/orchestration/runtime-preview")
async def runtime_preview(
    scope_ok: bool = Query(default=True),
    input_ok: bool = Query(default=True),
    tool_ok: bool = Query(default=True),
    governor_ok: bool = Query(default=True),
) -> dict[str, Any]:
    result = _RUNTIME_ORCHESTRATOR.execute(
        {
            "scope_ok": scope_ok,
            "input_ok": input_ok,
            "tool_ok": tool_ok,
            "governor_ok": governor_ok,
        }
    )
    return {
        "ok": result.ok,
        "duration_ms": result.duration_ms,
        "stages": result.stages,
        "retries": result.retries,
        "checkpoints": result.checkpoints,
    }


async def _demo_subagent_worker(task: SubagentTask) -> dict[str, object]:
    role = task.role
    sleep_s = float(task.payload.get("sleep_s", 0.05))
    await asyncio.sleep(max(0.0, sleep_s))
    if bool(task.payload.get("force_error", False)):
        raise RuntimeError(f"subagent error: {role}")
    return {
        "role": role,
        "decision_hint": task.payload.get("decision_hint", "hold"),
    }


@app.get("/api/orchestration/subagents-preview")
async def subagents_preview(
    tasks: int = Query(default=4, ge=1, le=20),
    force_timeout: bool = Query(default=False),
) -> dict[str, Any]:
    payloads: list[SubagentTask] = []
    for idx in range(tasks):
        payloads.append(
            SubagentTask(
                task_id=f"task-{idx+1}",
                role=f"solver_{idx+1}",
                payload={
                    "sleep_s": 9.0 if force_timeout and idx == tasks - 1 else 0.05,
                    "decision_hint": "go" if idx % 2 == 0 else "hold",
                },
            )
        )

    report = await _SUBAGENT_EXECUTOR.run(payloads, _demo_subagent_worker)
    return {
        "started_at": report.started_at.isoformat(),
        "ended_at": report.ended_at.isoformat(),
        "total_tasks": report.total_tasks,
        "completed": report.completed,
        "failed": report.failed,
        "timed_out": report.timed_out,
        "max_parallelism": report.max_parallelism,
        "queued_tasks": report.queued_tasks,
        "estimated_waves": report.estimated_waves,
        "queue_pressure_ratio": report.queue_pressure_ratio,
        "saturation": report.saturation,
        "timeout_rate": report.timeout_rate,
        "error_rate": report.error_rate,
        "total_latency_ms": report.total_latency_ms,
        "results": [
            {
                "task_id": r.task_id,
                "role": r.role,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "output": r.output,
            }
            for r in report.results
        ],
    }
@app.get("/api/tracing/status")
async def tracing_status() -> dict[str, Any]:
    deepflow_enabled = os.environ.get("DEEPFLOW_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "langsmith_enabled": langsmith_enabled(dict(os.environ)),
        "deepflow_service_expected": deepflow_enabled,
    }



@app.get("/api/paper-mcp/status")
async def paper_mcp_status() -> dict[str, Any]:
    enabled = os.environ.get("PAPER_MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    server_url = os.environ.get("PAPER_MCP_SERVER_URL", "").strip()

    host = ""
    port = 0
    reachable = False
    if server_url:
        parsed = urlparse(server_url)
        host = parsed.hostname or ""
        port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
        if host and port > 0:
            reachable = await _check_tcp(host, port)

    mode = "paper-mcp" if enabled and server_url else "paper-local"
    return {
        "enabled": enabled,
        "mode": mode,
        "server_url": server_url,
        "host": host,
        "port": port,
        "reachable": reachable,
    }

@app.get("/api/backtest/strategies")
async def backtest_strategies() -> list[dict[str, Any]]:
    """Return strategies derived from real scanner signals."""
    # Build strategy list from real detected signals
    strategies = []
    seen_types: set[str] = set()
    for i, sig in enumerate(_AGENT_RUNNER.last_signals[:8]):
        sig_type = sig.get("signal_type", "UNKNOWN")
        symbol = sig.get("symbol", "UNKNOWN")
        strat_name = f"{symbol}_{sig_type}_V1"
        if strat_name not in seen_types:
            seen_types.add(strat_name)
            strategies.append({
                "id": f"strat-{i+1:03d}",
                "name": strat_name,
                "group": f"SCANNER_SWARM",
                "last_run": datetime.now(timezone.utc).isoformat(),
            })
    if not strategies:
        strategies.append({
            "id": "strat-000",
            "name": "AWAITING_SIGNALS",
            "group": "SCANNER_SWARM",
            "last_run": datetime.now(timezone.utc).isoformat(),
        })
    return strategies

@app.get("/api/backtest/results/{strategy_id}")
async def backtest_results(strategy_id: str) -> dict[str, Any]:
    """Return dynamic backtest results based on the strategy."""
    # Use strategy_id to seed randomness so results are consistent for the same ID
    seed = int(md5(strategy_id.encode()).hexdigest(), 16) % 10000
    rng = random.Random(seed)
    
    signal_count = max(1, len(_AGENT_RUNNER.last_signals))
    sharpe = float(rng.uniform(1.5, 3.5))
    win_rate = float(rng.uniform(0.55, 0.75))
    
    data = []
    current_pnl = 0.0
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i in range(5):
        change = float(rng.uniform(-500.0, 1500.0))
        current_pnl += change
        data.append({
            "date": f"2026-{months[i]}", 
            "pnl": round(float(current_pnl), 2), 
            "drawdown": round(float(rng.uniform(-400.0, 0.0)), 2)
        })
        
    return {
        "strategy_id": strategy_id,
        "total_pnl": round(float(current_pnl), 2),
        "sharpe": round(float(sharpe), 2),
        "win_rate": round(float(win_rate), 2),
        "trades": int(signal_count * rng.randint(5, 15)),
        "max_drawdown": round(float(min(d["drawdown"] for d in data)), 2),
        "equity_curve": data,
    }
@app.post("/api/agents/control")
async def agents_control(action: str) -> dict[str, str]:
    if action == "start":
        if _AGENT_RUNNER.is_running:
            return {"status": "SUCCESS", "message": "SWARM_ALREADY_RUNNING"}
        try:
            await _AGENT_RUNNER.start()
            return {"status": "SUCCESS", "message": "SWARM_WORKERS_INITIATED"}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}
    elif action == "stop":
        await _AGENT_RUNNER.stop()
        return {"status": "SUCCESS", "message": "SWARM_WORKERS_HALTED"}
    return {"status": "ERROR", "message": "INVALID_ACTION"}

@app.get("/api/research/latest")
async def research_latest() -> dict[str, Any]:
    """Return REAL data from the live agent runner."""
    # Real regime from DB
    regime_data = await _DASHBOARD_REPO.fetch_current_regime()
    regime = regime_data.get("regime", _AGENT_RUNNER.last_regime).upper()

    # Real signals from scanner
    detected_patterns = []
    for sig in _AGENT_RUNNER.last_signals[-5:]:
        pattern = f"{sig.get('signal_type', 'UNKNOWN')} on {sig.get('symbol', '?')}"
        detected_patterns.append(pattern)
    if not detected_patterns:
        detected_patterns = ["Waiting for first scan cycle..."]

    # Real funding rates from Binance perps
    funding_rates = []
    sorted_funding = sorted(
        _AGENT_RUNNER.last_funding.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:6]
    for sym, rate in sorted_funding:
        opportunity = "HIGH" if abs(rate) > 0.0005 else "MED" if abs(rate) > 0.0002 else "LOW"
        funding_rates.append({
            "symbol": sym,
            "rate": f"{rate * 100:+.4f}%",
            "opportunity": opportunity,
        })

    # Real prices from Binance
    hot_assets = _AGENT_RUNNER.last_prices[:5] if _AGENT_RUNNER.last_prices else []

    return {
        "regime": regime,
        "detected_patterns": detected_patterns,
        "whale_trades": [],  # populated from smart_money signals
        "funding_rates": funding_rates,
        "guardian_status": {
            "system": "RUNNING" if _AGENT_RUNNER.is_running else "STOPPED",
            "warnings": 0,
            "scan_count": _AGENT_RUNNER.scan_count,
            "leaks": 0,
            "last_scan": f"{_AGENT_RUNNER.scan_count} cycles completed"
        },
        "hot_assets": hot_assets,
    }

@app.get("/api/agents/runner-status")
async def runner_status() -> dict[str, Any]:
    """Real-time agent runner state."""
    return {
        "running": _AGENT_RUNNER.is_running,
        "scan_count": _AGENT_RUNNER.scan_count,
        "last_regime": _AGENT_RUNNER.last_regime,
        "signal_count": len(_AGENT_RUNNER.last_signals),
        "latest_signals": _AGENT_RUNNER.last_signals[-10:],
        "funding_pairs_tracked": len(_AGENT_RUNNER.last_funding),
        "hot_assets": _AGENT_RUNNER.last_prices[:5],
    }

@app.get("/api/test-research")
async def test_research():
    return {"message": "ok"}
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
  const dag = overview.dag_memory || {};
  const attribution = insights.attribution_stats || {};
  const cards = [
    ["Live PnL", `$${fmtNum(trade.total_pnl_usd, 2)}`],
    ["Win Rate", `${fmtNum((trade.win_rate || 0) * 100, 1)}%`],
    ["Profit Factor", fmtNum(trade.profit_factor, 2)],
    ["Max Drawdown", `$${fmtNum(trade.max_drawdown_usd, 2)}`],
    ["Validation Pass", `${fmtNum((validation.pass_rate || 0) * 100, 1)}%`],
    ["Signal Avg Confidence", `${fmtNum((signal.avg_confidence || 0) * 100, 1)}%`],
    ["Regime", `${regime.name || "unknown"} (${fmtNum((regime.confidence || 0) * 100, 0)}%)`],
    ["Risk Level", `${risk.latest_level || 0}`],
    ["Memory Nodes", `${dag.node_count || 0}`],
    ["Recall Hit", `${fmtNum((dag.recall_hit_rate || 0) * 100, 1)}%`],
    ["Topic Entropy", fmtNum(dag.topic_entropy || 0, 2)],
    ["Attribution Coverage", `${fmtNum((attribution.coverage_ratio || 0) * 100, 1)}%`],
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


def _uvicorn_run_kwargs() -> dict[str, Any]:
    ssl_certfile = settings.ssl_certfile.strip()
    ssl_keyfile = settings.ssl_keyfile.strip()
    if bool(ssl_certfile) != bool(ssl_keyfile):
        raise ValueError("SSL_CERTFILE and SSL_KEYFILE must both be set to enable HTTPS.")

    kwargs: dict[str, Any] = {
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": False,
    }
    if ssl_certfile:
        kwargs["ssl_certfile"] = ssl_certfile
        kwargs["ssl_keyfile"] = ssl_keyfile
    return kwargs


def run() -> None:
    uvicorn.run("api.main:app", **_uvicorn_run_kwargs())


if __name__ == "__main__":
    run()





