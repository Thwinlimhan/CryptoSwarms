from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable


@dataclass(frozen=True)
class AgentSnapshot:
    name: str
    last_heartbeat: str | None
    signals_today: int
    status: str


def classify_health(now: datetime, last_heartbeat: datetime | None, stale_after_seconds: int = 180) -> str:
    if last_heartbeat is None:
        return "stale"
    delta = now - last_heartbeat
    return "healthy" if delta <= timedelta(seconds=stale_after_seconds) else "stale"


def build_agent_snapshots(
    *,
    now: datetime,
    agents: Iterable[str],
    heartbeat_lookup: dict[str, datetime | None],
    signal_counts: dict[str, int],
    stale_after_seconds: int = 180,
) -> dict[str, dict[str, object]]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    out: dict[str, dict[str, object]] = {}
    for agent in agents:
        last = heartbeat_lookup.get(agent)
        out[agent] = {
            "last_heartbeat": last.isoformat() if last else None,
            "signals_today": int(signal_counts.get(agent, 0)),
            "status": classify_health(now, last, stale_after_seconds=stale_after_seconds),
        }
    return out
