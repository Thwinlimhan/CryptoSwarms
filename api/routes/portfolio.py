"""Portfolio API — real-time PnL dashboard endpoint.

Provides live portfolio data including total PnL, open positions,
daily PnL, and risk metrics for real-time monitoring.
Connected to the live PositionManager and OrderPersistence.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PortfolioTracker:
    """Track live portfolio state for the dashboard API.

    Connects to the PositionManager and OrderPersistence instances
    running in the AgentRunner.
    """

    def __init__(self) -> None:
        self._positions: list[dict[str, Any]] = []
        self._daily_pnl_history: list[dict[str, Any]] = []
        self._total_pnl: float = 0.0
        self._equity_curve: list[dict[str, Any]] = []
        self._trade_history: list[dict[str, Any]] = []
        self._last_update: float = 0.0

        # References to live components (set by AgentRunner)
        self._position_manager: Any = None
        self._order_persistence: Any = None
        self._ws_manager: Any = None

    def connect_position_manager(self, pm: Any) -> None:
        """Connect to the live PositionManager instance."""
        self._position_manager = pm

    def connect_order_persistence(self, persistence: Any) -> None:
        """Connect to the live OrderPersistence instance."""
        self._order_persistence = persistence

    def connect_ws_manager(self, ws_manager: Any) -> None:
        """Connect to the WebSocket manager for broadcasting."""
        self._ws_manager = ws_manager

    def _sync_from_position_manager(self) -> None:
        """Pull latest data from the live PositionManager."""
        pm = self._position_manager
        if pm is None:
            return

        now = time.monotonic()
        # Throttle to every 1s to avoid overhead
        if now - self._last_update < 1.0:
            return
        self._last_update = now

        # Sync open positions
        self._positions = []
        for pos_id, pos in pm.open_positions.items():
            side_str = pos.side.value if hasattr(pos.side, "value") else str(pos.side)
            self._positions.append({
                "position_id": pos.position_id,
                "strategy_id": pos.strategy_id,
                "symbol": pos.symbol,
                "side": side_str,
                "entry_price": pos.entry_price,
                "size_usd": round(pos.size_usd, 2),
                "size_tokens": round(pos.size_tokens, 6),
                "stop_loss": round(pos.stop_loss_price, 4),
                "take_profit": round(pos.take_profit_price, 4),
                "unrealized_pnl": round(pos.unrealized_pnl, 2),
                "candles_held": pos.candles_held,
                "entry_time": pos.entry_time.isoformat(),
                "highest_price": pos.highest_price,
                "lowest_price": pos.lowest_price,
            })

        # Sync total realized PnL
        self._total_pnl = pm.total_pnl

        # Sync trade history
        self._trade_history = []
        for trade in pm.closed_trades[-50:]:  # Last 50 trades
            self._trade_history.append({
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "strategy_id": trade.strategy_id,
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "size_usd": trade.size_usd,
                "pnl_usd": trade.pnl_usd,
                "pnl_pct": trade.pnl_pct,
                "fees_usd": trade.fees_usd,
                "exit_reason": trade.exit_reason,
                "hold_duration_seconds": trade.hold_duration_seconds,
                "exit_time": trade.exit_time.isoformat(),
            })

    def update_positions(self, positions: list[dict[str, Any]]) -> None:
        self._positions = positions

    def update_pnl(self, total_pnl: float, daily_entry: dict[str, Any] | None = None) -> None:
        self._total_pnl = total_pnl
        if daily_entry:
            self._daily_pnl_history.append(daily_entry)
            # Keep last 90 days
            self._daily_pnl_history = self._daily_pnl_history[-90:]

    def record_equity_point(self, equity_usd: float) -> None:
        """Record an equity curve data point."""
        self._equity_curve.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity_usd": round(equity_usd, 2),
        })
        # Keep last 1000 points
        self._equity_curve = self._equity_curve[-1000:]

    def get_total_pnl(self) -> float:
        self._sync_from_position_manager()
        return self._total_pnl

    def get_open_positions(self) -> list[dict[str, Any]]:
        self._sync_from_position_manager()
        return list(self._positions)

    def get_daily_pnl(self) -> list[dict[str, Any]]:
        return list(self._daily_pnl_history)

    def get_trade_history(self) -> list[dict[str, Any]]:
        self._sync_from_position_manager()
        return list(self._trade_history)

    def get_risk_metrics(self) -> dict[str, Any]:
        self._sync_from_position_manager()
        total_exposure = sum(p.get("size_usd", 0) for p in self._positions)
        position_count = len(self._positions)

        # Calculate max single position exposure
        max_position = max(
            (p.get("size_usd", 0) for p in self._positions), default=0
        )

        # Unrealized PnL across open positions
        unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in self._positions)

        # Performance metrics from PositionManager
        pm = self._position_manager
        win_rate = pm.win_rate if pm else 0.0
        profit_factor = pm.profit_factor if pm else 0.0
        total_trades = len(pm.closed_trades) if pm else 0

        return {
            "total_exposure_usd": round(total_exposure, 2),
            "position_count": position_count,
            "max_single_position_usd": round(max_position, 2),
            "concentration_risk": (
                round(max_position / total_exposure * 100, 1)
                if total_exposure > 0
                else 0.0
            ),
            "unrealized_pnl_usd": round(unrealized_pnl, 2),
            "win_rate": round(win_rate * 100, 1),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.99,
            "total_closed_trades": total_trades,
        }

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        """Complete portfolio snapshot for WebSocket broadcast."""
        return {
            "total_pnl_usd": self.get_total_pnl(),
            "open_positions": self.get_open_positions(),
            "risk_metrics": self.get_risk_metrics(),
            "trade_count": len(self._trade_history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_order_stats(self) -> dict[str, Any]:
        """Get order persistence statistics."""
        if self._order_persistence is not None:
            return self._order_persistence.get_order_stats()
        return {"total_orders": 0, "by_status": {}, "pending_count": 0, "filled_count": 0, "failed_count": 0}

    async def get_recent_orders(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent orders from persistence."""
        if self._order_persistence is None:
            return []
        orders = await self._order_persistence.get_all_orders()
        result = []
        for o in orders[-limit:]:
            result.append({
                "client_order_id": o.client_order_id,
                "symbol": o.symbol,
                "side": o.side,
                "order_type": o.order_type,
                "quantity": o.quantity,
                "price": o.price,
                "strategy_id": o.strategy_id,
                "status": o.status.value,
                "created_at": o.created_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
                "exchange_order_id": o.exchange_order_id,
                "filled_quantity": o.filled_quantity,
                "filled_price": o.filled_price,
                "error_message": o.error_message,
            })
        return result


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
        "trade_history": portfolio_tracker.get_trade_history()[-10:],
    }


@router.get("/positions")
async def get_positions() -> dict[str, Any]:
    """List all open positions."""
    positions = portfolio_tracker.get_open_positions()
    return {
        "positions": positions,
        "count": len(positions),
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


@router.get("/trades")
async def get_trade_history() -> dict[str, Any]:
    """Closed trade history."""
    trades = portfolio_tracker.get_trade_history()
    return {
        "trades": trades,
        "count": len(trades),
        "total_pnl_usd": portfolio_tracker.get_total_pnl(),
    }


@router.get("/orders")
async def get_orders() -> dict[str, Any]:
    """Order persistence data."""
    orders = await portfolio_tracker.get_recent_orders()
    stats = await portfolio_tracker.get_order_stats()
    return {
        "orders": orders,
        "stats": stats,
    }


@router.get("/summary")
async def get_portfolio_summary() -> dict[str, Any]:
    """Complete portfolio summary with performance stats."""
    pm = portfolio_tracker._position_manager
    summary = pm.summary() if pm else {"trades": 0, "message": "No position manager connected"}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "performance": summary,
        "risk_metrics": portfolio_tracker.get_risk_metrics(),
        "order_stats": await portfolio_tracker.get_order_stats(),
    }
