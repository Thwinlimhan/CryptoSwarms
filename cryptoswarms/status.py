from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class AgentHeartbeat:
    name: str
    last_heartbeat: datetime | None
    signals_today: int


def is_heartbeat_fresh(last_heartbeat: datetime | None, ttl_seconds: int = 120) -> bool:
    if last_heartbeat is None:
        return False
    now = datetime.now(timezone.utc)
    if last_heartbeat.tzinfo is None:
        last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
    return now - last_heartbeat <= timedelta(seconds=ttl_seconds)


def build_agent_status(heartbeats: list[AgentHeartbeat], ttl_seconds: int = 120) -> dict[str, dict[str, str | int]]:
    """Build Mission Control-friendly status payload."""

    payload: dict[str, dict[str, str | int]] = {}
    for item in heartbeats:
        payload[item.name] = {
            "last_heartbeat": item.last_heartbeat.isoformat() if item.last_heartbeat else "",
            "signals_today": item.signals_today,
            "status": "healthy" if is_heartbeat_fresh(item.last_heartbeat, ttl_seconds) else "stale",
        }
    return payload
