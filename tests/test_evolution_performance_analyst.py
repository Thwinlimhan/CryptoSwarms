from datetime import datetime, timezone

from agents.evolution.performance_analyst import generate_daily_report, publish_daily_report


class FakeDB:
    def __init__(self):
        self.queries = []

    def fetchall(self, sql: str, params=()):
        self.queries.append((sql, params))
        if "FROM trades" in sql:
            return [("s1", 10.0), ("s2", -2.0)]
        if "FROM llm_costs" in sql:
            return [(1.25,)]
        return []


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish(self, channel: str, payload: dict[str, object]) -> None:
        self.events.append((channel, payload))


def test_generate_and_publish_daily_report():
    report = generate_daily_report(FakeDB(), now=datetime(2026, 3, 8, tzinfo=timezone.utc))
    assert report.daily_pnl_usd == 8.0
    assert report.best_strategy == "s1"

    pub = FakePublisher()
    publish_daily_report(report, pub)
    channels = [c for c, _ in pub.events]
    assert "redis:evolution:daily_report" in channels
    assert "mission-control:daily_report" in channels
