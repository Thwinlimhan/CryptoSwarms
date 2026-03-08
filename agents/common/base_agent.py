from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agents.common import streams
from agents.common.stream_bus import StreamBus


class BaseAgent:
    def __init__(self, agent_id: str, stream_bus: StreamBus):
        self.agent_id = agent_id
        self.stream_bus = stream_bus
        self.logger = logging.getLogger(agent_id)

    def heartbeat(self, status: str = "healthy", **extra: Any) -> str:
        payload: dict[str, Any] = {
            "agent_id": self.agent_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        return self.stream_bus.redis.xadd(
            streams.AGENT_HEARTBEATS,
            {"event": json.dumps(payload)},
        )

    def log_event(self, event: str, level: int = logging.INFO, **fields: Any) -> None:
        record = {
            "agent_id": self.agent_id,
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self.logger.log(level, json.dumps(record, sort_keys=True))
