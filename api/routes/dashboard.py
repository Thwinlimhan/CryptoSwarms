from fastapi import APIRouter, Query
from typing import Any
from datetime import datetime, timezone
from api.utils import readiness_checks, compute_dag_memory_stats, build_lineage_summary
from api.dependencies import dashboard_repo, REGISTERED_AGENTS
from cryptoswarms.dashboard_insights import build_dashboard_insights
from cryptoswarms.status_dashboard import build_agent_snapshots

router = APIRouter(tags=["dashboard"])

@router.get("/api/portfolio/equity-curve")
async def portfolio_equity_curve(lookback_hours: int = Query(default=168, ge=1, le=720)) -> list[dict[str, Any]]:
    return await dashboard_repo.fetch_equity_curve(lookback_hours=lookback_hours)

@router.get("/api/regime/current")
async def regime_current() -> dict[str, Any]:
    return await dashboard_repo.fetch_current_regime()

@router.get("/api/strategies/pending-validation")
async def pending_validation() -> list[dict[str, Any]]:
    return await dashboard_repo.fetch_pending_validation()

@router.get("/api/agents/status")
async def agents_status() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    heartbeats = await dashboard_repo.fetch_redis_heartbeats()
    signal_counts = await dashboard_repo.fetch_signal_counts()
    return build_agent_snapshots(
        now=now,
        agents=REGISTERED_AGENTS,
        heartbeat_lookup=heartbeats,
        signal_counts=signal_counts,
        stale_after_seconds=180,
    )

@router.get("/api/dashboard/overview")
async def dashboard_overview() -> dict[str, Any]:
    readiness = await readiness_checks()
    statuses = await agents_status()
    stale = [name for name, payload in statuses.items() if payload["status"] != "healthy"]
    total_signals_today = sum(int(payload.get("signals_today", 0)) for payload in statuses.values())
    dag_memory = compute_dag_memory_stats()
    traces = await dashboard_repo.fetch_live_trade_traces(limit=300)
    attribution_lineage = build_lineage_summary(traces=traces)
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

@router.get("/api/dashboard/insights")
async def dashboard_insights(lookback_hours: int = Query(default=168, ge=1, le=720)) -> dict[str, Any]:
    data = await dashboard_repo.fetch_dashboard_insight_inputs(lookback_hours)
    return build_dashboard_insights(data)
