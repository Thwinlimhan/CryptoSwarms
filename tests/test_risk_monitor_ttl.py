from datetime import datetime, timezone

from agents.execution.risk_monitor import InMemoryRiskEventLogger, RiskMonitor, RiskState


class StubPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


class StubHeartbeatStore:
    def __init__(self) -> None:
        self.calls = []

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.calls.append((key, ttl_seconds, value))


def test_risk_monitor_writes_ttl_heartbeat():
    store = StubHeartbeatStore()
    monitor = RiskMonitor(
        event_publisher=StubPublisher(),
        risk_event_logger=InMemoryRiskEventLogger(),
        heartbeat_store=store,
        heartbeat_ttl_seconds=600,
    )

    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    monitor.publish_heartbeat(now)

    assert len(store.calls) == 1
    key, ttl, value = store.calls[0]
    assert key == "risk_monitor:heartbeat"
    assert ttl == 600
    assert "2026-03-08" in value
