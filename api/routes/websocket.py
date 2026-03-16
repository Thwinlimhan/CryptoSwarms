"""WebSocket endpoint for live dashboard updates.

Broadcasts real-time data to connected frontend clients:
  - Market signals and hot assets
  - Portfolio PnL updates
  - Order lifecycle events
  - Trade closures
  - Market data from Binance WS
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("api.ws")
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections with channel subscriptions."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._broadcast_count = 0
        self._last_broadcast_at: float = 0.0

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WS connected (%d active)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WS disconnected (%d active)", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all active WebSocket clients."""
        if not self.active_connections:
            return

        self._broadcast_count += 1
        self._last_broadcast_at = time.monotonic()

        dead_connections: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(connection)

    async def broadcast_portfolio_update(
        self,
        total_pnl: float,
        positions: list[dict[str, Any]],
        risk_metrics: dict[str, Any],
        daily_pnl: list[dict[str, Any]] | None = None,
    ) -> None:
        """Broadcast a portfolio update to all clients."""
        await self.broadcast({
            "type": "portfolio_update",
            "data": {
                "total_pnl_usd": total_pnl,
                "positions": positions,
                "risk_metrics": risk_metrics,
                "daily_pnl": daily_pnl or [],
                "timestamp": time.time(),
            },
        })

    async def broadcast_order_event(
        self,
        event: str,
        order_data: dict[str, Any],
    ) -> None:
        """Broadcast order lifecycle event (created, submitted, filled, failed)."""
        await self.broadcast({
            "type": "order_event",
            "event": event,
            "data": order_data,
        })

    async def broadcast_market_data(
        self,
        hot_assets: list[dict[str, Any]],
    ) -> None:
        """Broadcast market data update from WebSocket stream."""
        await self.broadcast({
            "type": "market_data",
            "data": {
                "hot_assets": hot_assets,
                "timestamp": time.time(),
            },
        })

    def get_stats(self) -> dict[str, Any]:
        """Return WebSocket connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "total_broadcasts": self._broadcast_count,
            "last_broadcast_at": self._last_broadcast_at,
        }


manager = ConnectionManager()


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket) -> None:
    """Entry point for the live WebSocket feed."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client sends pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                # Handle JSON commands from frontend
                try:
                    cmd = json.loads(data)
                    cmd_type = cmd.get("type", "")

                    if cmd_type == "subscribe":
                        # Client subscribing to specific channels
                        await websocket.send_json({
                            "type": "subscribed",
                            "channels": cmd.get("channels", []),
                        })
                    elif cmd_type == "request_portfolio":
                        # Client requesting immediate portfolio snapshot
                        await websocket.send_json({
                            "type": "portfolio_snapshot_ack",
                            "message": "Portfolio snapshot will be sent on next update cycle",
                        })
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)
