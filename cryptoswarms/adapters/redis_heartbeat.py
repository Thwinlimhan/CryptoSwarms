"""Async Redis adapter for agent heartbeats.

Agents write their heartbeats here so the dashboard can check freshness.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RedisHeartbeat:
    """Manages agent heartbeats in Redis with TTL."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: object | None = None

    async def connect(self) -> None:
        try:
            from redis.asyncio import from_url
            self._client = from_url(self._redis_url, encoding="utf-8", decode_responses=True)
            await self._client.ping()
            logger.info("RedisHeartbeat connected")
        except Exception as exc:
            logger.warning("RedisHeartbeat could not connect: %s", exc)
            self._client = None

    async def close(self) -> None:
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass

    async def set_heartbeat(self, agent_name: str, ttl_seconds: int = 600) -> bool:
        """Write heartbeat for ``agent_name`` with a TTL."""
        if not self._client:
            return False
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._client.setex(f"heartbeat:{agent_name}", ttl_seconds, now)
            return True
        except Exception as exc:
            logger.warning("Failed to set heartbeat for %s: %s", agent_name, exc)
            return False

    async def get_heartbeat(self, agent_name: str) -> str | None:
        if not self._client:
            return None
        try:
            return await self._client.get(f"heartbeat:{agent_name}")
        except Exception:
            return None
