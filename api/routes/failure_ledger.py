from fastapi import APIRouter, Query
from typing import Any
from api.dependencies import dashboard_repo

router = APIRouter(tags=["failure-ledger"])

@router.get("/api/failure-ledger/decisions")
async def get_decisions(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    """Retrieve decisions recorded in the failure ledger."""
    return await dashboard_repo.fetch_decisions(limit=limit)

@router.get("/api/failure-ledger/stats")
async def get_ledger_stats() -> dict[str, Any]:
    """Calculate aggregated stats for the ledger."""
    decisions = await dashboard_repo.fetch_decisions(limit=1000)
    resolved = [d for d in decisions if d["status"] in ["won", "lost"]]
    
    if not resolved:
        return {"status": "NO_DATA"}
        
    actual_pnl = sum(float(d.get("pnl_usd") or 0.0) for d in resolved)
    expected_pnl = sum(float(d.get("ev_estimate") or 0.0) for d in resolved)
    
    actual_wins = sum(1 for d in resolved if d["status"] == "won")
    expected_wins = sum(float(d.get("win_probability") or 0.0) for d in resolved)
    
    return {
        "count": len(resolved),
        "net_luck": actual_pnl - expected_pnl,
        "calibration_error": (actual_wins - expected_wins) / len(resolved),
        "actual_win_rate": actual_wins / len(resolved),
        "expected_win_rate": expected_wins / len(resolved)
    }
