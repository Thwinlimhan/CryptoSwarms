"""WebSocket Manager — persistent WebSocket connections with automatic reconnection.

Manages connections to exchange WebSocket feeds with exponential backoff
reconnection, ensuring data freshness.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("swarm.adapters.websocket")


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionStats:
    """Connection statistics for a single WebSocket."""
    url: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    reconnect_attempts: int = 0
    total_reconnects: int = 0
    messages_received: int = 0
    last_message_at: datetime | None = None
    connected_at: datetime | None = None
    last_error: str | None = None


class ExchangeWebSocket:
    """WebSocket connection manager with exponential backoff reconnection.

    Manages a single persistent WebSocket connection to an exchange feed,
    automatically reconnecting on disconnection with exponential backoff.
    """

    def __init__(
        self,
        url: str,
        *,
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        max_reconnects: int = 50,
        max_backoff_seconds: float = 300.0,
        ping_interval: float = 30.0,
    ) -> None:
        self.url = url
        self._on_message = on_message
        self.max_reconnects = max_reconnects
        self.max_backoff_seconds = max_backoff_seconds
        self.ping_interval = ping_interval
        self.reconnect_attempts = 0
        self._connection: Any = None
        self._running = False
        self._stats = ConnectionStats(url=url)
        self._task: asyncio.Task[None] | None = None

    async def _connect(self) -> Any:
        """Establish the WebSocket connection."""
        try:
            import websockets  # type: ignore
        except ImportError:
            logger.error("websockets package not installed")
            raise

        self._stats.state = ConnectionState.CONNECTING
        connection = await websockets.connect(
            self.url,
            ping_interval=self.ping_interval,
            close_timeout=10,
        )
        self._stats.state = ConnectionState.CONNECTED
        self._stats.connected_at = datetime.now(timezone.utc)
        logger.info("WebSocket connected to %s", self.url)
        return connection

    async def connect_with_backoff(self) -> None:
        """Connect with exponential backoff on failures.

        Will attempt to reconnect up to max_reconnects times,
        with wait times doubling after each failure (capped at max_backoff_seconds).
        """
        self._running = True
        self.reconnect_attempts = 0

        while self._running and self.reconnect_attempts < self.max_reconnects:
            try:
                self._connection = await self._connect()
                self.reconnect_attempts = 0
                await self._listen()
            except asyncio.CancelledError:
                logger.info("WebSocket task cancelled for %s", self.url)
                break
            except Exception as exc:
                self._stats.last_error = str(exc)
                self._stats.state = ConnectionState.RECONNECTING
                self.reconnect_attempts += 1
                self._stats.total_reconnects += 1

                wait_time = min(
                    self.max_backoff_seconds,
                    2 ** self.reconnect_attempts,
                )
                logger.warning(
                    "WebSocket disconnected from %s (attempt %d/%d). "
                    "Reconnecting in %.0fs: %s",
                    self.url, self.reconnect_attempts, self.max_reconnects,
                    wait_time, exc,
                )
                await asyncio.sleep(wait_time)

        if self.reconnect_attempts >= self.max_reconnects:
            self._stats.state = ConnectionState.FAILED
            logger.error(
                "WebSocket permanently failed for %s after %d attempts",
                self.url, self.max_reconnects,
            )

    async def _listen(self) -> None:
        """Listen for messages on the WebSocket connection."""
        if self._connection is None:
            return

        async for message in self._connection:
            self._stats.messages_received += 1
            self._stats.last_message_at = datetime.now(timezone.utc)

            if self._on_message is not None:
                try:
                    import json
                    data = json.loads(message) if isinstance(message, str) else message
                    await self._on_message(data)
                except Exception as exc:
                    logger.error("Error processing WebSocket message: %s", exc)

    async def start(self) -> None:
        """Start the WebSocket connection in a background task."""
        self._task = asyncio.create_task(self.connect_with_backoff())

    async def stop(self) -> None:
        """Gracefully stop the WebSocket connection."""
        self._running = False
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:
                pass
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._stats.state = ConnectionState.DISCONNECTED

    @property
    def stats(self) -> ConnectionStats:
        return self._stats

    @property
    def is_connected(self) -> bool:
        return self._stats.state == ConnectionState.CONNECTED


class WebSocketManager:
    """Manages multiple exchange WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[str, ExchangeWebSocket] = {}

    def add_connection(
        self,
        name: str,
        ws: ExchangeWebSocket,
    ) -> None:
        """Register a named WebSocket connection."""
        self._connections[name] = ws

    async def start_all(self) -> None:
        """Start all registered WebSocket connections."""
        for name, ws in self._connections.items():
            logger.info("Starting WebSocket: %s", name)
            await ws.start()

    async def stop_all(self) -> None:
        """Stop all registered WebSocket connections."""
        for name, ws in self._connections.items():
            logger.info("Stopping WebSocket: %s", name)
            await ws.stop()

    def get_status(self) -> dict[str, Any]:
        """Return status of all managed connections."""
        return {
            name: {
                "state": ws.stats.state.value,
                "messages_received": ws.stats.messages_received,
                "reconnect_attempts": ws.stats.reconnect_attempts,
                "total_reconnects": ws.stats.total_reconnects,
                "last_message_at": (
                    ws.stats.last_message_at.isoformat()
                    if ws.stats.last_message_at else None
                ),
                "last_error": ws.stats.last_error,
            }
            for name, ws in self._connections.items()
        }
