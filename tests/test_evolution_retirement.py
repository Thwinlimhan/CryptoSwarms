from agents.evolution.retirement import evaluate_retirement, retire_underperformers


class FakeDB:
    def __init__(self):
        self.exec_calls = []

    def fetchall(self, sql: str, params=()):
        return [("s1", 0.4), ("s2", 0.8)]

    def execute(self, sql: str, params=()):
        self.exec_calls.append((sql, params))


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish(self, channel: str, payload: dict[str, object]) -> None:
        self.events.append((channel, payload))


def test_evaluate_retirement_threshold():
    retired, _ = evaluate_retirement(0.3, threshold=0.5)
    assert retired is True


def test_retire_underperformers_updates_and_publishes():
    db = FakeDB()
    pub = FakePublisher()

    decisions = retire_underperformers(db, pub, threshold=0.5)

    assert any(d.strategy_id == "s1" and d.retired for d in decisions)
    assert len(db.exec_calls) == 1
    assert pub.events[0][0] == "evolution:retire"
