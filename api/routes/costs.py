from fastapi import APIRouter, Query
from typing import Any
from cryptoswarms.budget_guard import BudgetConfig, evaluate_budget
from api.dependencies import agent_runner

router = APIRouter(prefix="/api/costs", tags=["costs"])

@router.get("/budget")
async def costs_budget(spent_usd: float = Query(default=0.0, ge=0.0)) -> dict[str, Any]:
    status = evaluate_budget(spent_usd=spent_usd, config=BudgetConfig())
    return {
        "spent_usd": status.spent_usd,
        "daily_budget_usd": status.budget_usd,
        "alert_threshold_usd": status.alert_threshold_usd,
        "within_budget": status.within_budget,
        "alert": status.alert,
        "blocked": status.blocked,
    }

@router.get("/daily")
async def costs_daily() -> list[dict[str, Any]]:
    import asyncpg
    from api.dependencies import _timescale_dsn_str
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
        import logging
        logging.getLogger(__name__).debug("costs_daily failed", exc_info=True)
    
    # Fallback: estimate from agent scan count
    scans = agent_runner.scan_count
    return [
        {"agent": "market_scanner", "model": "binance-api", "total_usd": round(scans * 0.0001, 4), "_estimated": True},
        {"agent": "regime_classifier", "model": "binance-api", "total_usd": round(scans * 0.00005, 4), "_estimated": True},
    ]
