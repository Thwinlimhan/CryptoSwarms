"""Portfolio API — real-time PnL dashboard endpoint.

Provides live portfolio data including total PnL, open positions,
daily PnL, and risk metrics for real-time monitoring.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PortfolioTracker:
    """Track live portfolio state for the dashboard API.

    In production, this would be backed by a database + the PositionManager.
    Here we provide the interface and in-memory fallback.
    """

    def __init__(self) -> None:
        self._positions: list[dict[str, Any]] = []
        self._daily_pnl_history: list[dict[str, Any]] = []
        self._total_pnl: float = 0.0

    def update_positions(self, positions: list[dict[str, Any]]) -> None:
        self._positions = positions

    def update_pnl(self, total_pnl: float, daily_entry: dict[str, Any] | None = None) -> None:
        self._total_pnl = total_pnl
        if daily_entry:
            self._daily_pnl_history.append(daily_entry)
            # Keep last 90 days
            self._daily_pnl_history = self._daily_pnl_history[-90:]

    def get_total_pnl(self) -> float:
        return self._total_pnl

    def get_open_positions(self) -> list[dict[str, Any]]:
        return list(self._positions)

    def get_daily_pnl(self) -> list[dict[str, Any]]:
        return list(self._daily_pnl_history)

    def get_risk_metrics(self) -> dict[str, Any]:
        total_exposure = sum(p.get("size_usd", 0) for p in self._positions)
        position_count = len(self._positions)

        # Calculate max single position exposure
        max_position = max(
            (p.get("size_usd", 0) for p in self._positions), default=0
        )

        return {
            "total_exposure_usd": round(total_exposure, 2),
            "position_count": position_count,
            "max_single_position_usd": round(max_position, 2),
            "concentration_risk": (
                round(max_position / total_exposure * 100, 1)
                if total_exposure > 0
                else 0.0
            ),
        }


# Module-level tracker instance
portfolio_tracker = PortfolioTracker()


@router.get("/live")
async def get_live_portfolio() -> dict[str, Any]:
    """Real-time portfolio overview."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_pnl_usd": portfolio_tracker.get_total_pnl(),
        "open_positions": portfolio_tracker.get_open_positions(),
        "daily_pnl": portfolio_tracker.get_daily_pnl(),
        "risk_metrics": portfolio_tracker.get_risk_metrics(),
    }


@router.get("/positions")
async def get_positions() -> dict[str, Any]:
    """List all open positions."""
    return {
        "positions": portfolio_tracker.get_open_positions(),
        "count": len(portfolio_tracker.get_open_positions()),
    }


@router.get("/risk")
async def get_risk() -> dict[str, Any]:
    """Current risk metrics."""
    return portfolio_tracker.get_risk_metrics()


@router.get("/pnl/daily")
async def get_daily_pnl() -> dict[str, Any]:
    """Daily PnL history."""
    return {
        "daily_pnl": portfolio_tracker.get_daily_pnl(),
        "total_pnl_usd": portfolio_tracker.get_total_pnl(),
    }
