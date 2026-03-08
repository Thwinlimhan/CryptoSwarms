from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class KeyValueStore(Protocol):
    def set(self, key: str, value: str) -> None: ...

    def get(self, key: str) -> str | None: ...


@dataclass(frozen=True)
class HeartbeatRecord:
    component: str
    timestamp: datetime


def _utc_iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    parsed = datetime.fromisoformat(ts)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def heartbeat_key(component: str) -> str:
    return f"heartbeat:{component}"


def set_heartbeat(store: KeyValueStore, record: HeartbeatRecord) -> None:
    store.set(heartbeat_key(record.component), _utc_iso(record.timestamp))


def get_heartbeat(store: KeyValueStore, component: str) -> datetime | None:
    raw = store.get(heartbeat_key(component))
    if raw is None or not raw.strip():
        return None
    return _parse_iso(raw)
