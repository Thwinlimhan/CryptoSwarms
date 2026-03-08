from datetime import datetime, timezone

from cryptoswarms.storage import HeartbeatRecord, get_heartbeat, set_heartbeat


class InMemoryKV:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str | None:
        return self.data.get(key)


def test_set_and_get_heartbeat_roundtrip():
    store = InMemoryKV()
    ts = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)

    set_heartbeat(store, HeartbeatRecord(component="risk_monitor", timestamp=ts))
    loaded = get_heartbeat(store, "risk_monitor")

    assert loaded == ts
