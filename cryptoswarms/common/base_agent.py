from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from . import streams
from .stream_bus import StreamBus


class BaseAgent(ABC):
    """Abstract base class for all swarm agents."""

    def __init__(self, agent_id: str, stream_bus: StreamBus | None = None):
        self.agent_id = agent_id
        self.stream_bus = stream_bus
        self.logger = logging.getLogger(agent_id)
        self._started_at: datetime | None = None

    @abstractmethod
    async def run_cycle(self) -> Any:
        """Execute one cycle of this agent's work."""
        ...

    def heartbeat(self, status: str = "healthy", **extra: Any) -> str | None:
        """Emit a standardized heartbeat to Redis Streams."""
        if self.stream_bus is None:
            return None
        payload = {
            "agent_id": self.agent_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        return self.stream_bus.redis.xadd(
            streams.AGENT_HEARTBEATS,
            {"event": json.dumps(payload)},
        )

    def status(self) -> dict[str, Any]:
        """Return standardized health dict for the agent."""
        return {
            "agent_id": self.agent_id,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "status": "running" if self._started_at else "stopped",
        }
