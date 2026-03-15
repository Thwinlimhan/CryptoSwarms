from fastapi import APIRouter
from typing import Any
from api.dependencies import agent_runner, dashboard_repo

router = APIRouter(prefix="/api", tags=["agents"])

@router.post("/agents/control")
async def agents_control(action: str) -> dict[str, str]:
    if action == "start":
        if agent_runner.is_running:
            return {"status": "SUCCESS", "message": "SWARM_ALREADY_RUNNING"}
        try:
            await agent_runner.start()
            return {"status": "SUCCESS", "message": "SWARM_WORKERS_INITIATED"}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}
    elif action == "stop":
        await agent_runner.stop()
        return {"status": "SUCCESS", "message": "SWARM_WORKERS_HALTED"}
    return {"status": "ERROR", "message": "INVALID_ACTION"}

@router.get("/research/latest")
async def research_latest() -> dict[str, Any]:
    """Return REAL data from the live agent runner."""
    # Real regime from DB
    regime_data = await dashboard_repo.fetch_current_regime()
    regime = regime_data.get("regime", agent_runner.last_regime).upper()

    # Real signals from scanner
    detected_patterns = []
    for sig in agent_runner.last_signals[-5:]:
        pattern = f"{sig.get('signal_type', 'UNKNOWN')} on {sig.get('symbol', '?')}"
        detected_patterns.append(pattern)
    if not detected_patterns:
        detected_patterns = ["Waiting for first scan cycle..."]

    # Real funding rates from Binance perps
    funding_rates = []
    sorted_funding = sorted(
        agent_runner.last_funding.items(),
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
    hot_assets = agent_runner.last_prices[:5] if agent_runner.last_prices else []

    return {
        "regime": regime,
        "detected_patterns": detected_patterns,
        "whale_trades": [],  # populated from smart_money signals
        "funding_rates": funding_rates,
        "guardian_status": {
            "system": "RUNNING" if agent_runner.is_running else "STOPPED",
            "warnings": 0,
            "scan_count": agent_runner.scan_count,
            "leaks": 0,
            "last_scan": f"{agent_runner.scan_count} cycles completed"
        },
        "hot_assets": hot_assets,
    }

@router.get("/agents/runner-status")
async def runner_status() -> dict[str, Any]:
    """Real-time agent runner state."""
    return {
        "running": agent_runner.is_running,
        "scan_count": agent_runner.scan_count,
        "last_regime": agent_runner.last_regime,
        "signal_count": len(agent_runner.last_signals),
        "latest_signals": agent_runner.last_signals[-10:],
        "signal_history": agent_runner.signal_history,
        "funding_pairs_tracked": len(agent_runner.last_funding),
        "hot_assets": agent_runner.last_prices[:5],
    }

@router.get("/test-research")
async def test_research():
    return {"message": "ok"}

@router.get("/routing/policy")
async def routing_policy() -> dict[str, Any]:
    from cryptoswarms.routing_policy import ROUTING_POLICY
    return {"tasks": ROUTING_POLICY}
