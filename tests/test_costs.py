from datetime import datetime, timedelta, timezone

from cryptoswarms.costs import (
    LlmCostEvent,
    ensure_costs_schema,
    read_daily_cost_totals,
    write_llm_cost,
)


class FakeDB:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[object, ...]]] = []
        self.rows: list[tuple[object, ...]] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        self.commands.append((sql, params))

    def fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
        self.commands.append((sql, params))
        return self.rows


def test_schema_and_write_cost(monkeypatch):
    db = FakeDB()
    seen: dict[str, object] = {}

    def fake_emit(event, env):
        seen["agent"] = event.agent
        return True

    monkeypatch.setattr("cryptoswarms.costs.emit_langsmith_trace", fake_emit)

    ensure_costs_schema(db)
    write_llm_cost(
        db,
        LlmCostEvent(
            timestamp=datetime.now(timezone.utc),
            agent="scanner",
            model="qwen3.5-4b-local",
            cost_usd=0.0,
        ),
        trace_env={"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "k", "LANGCHAIN_PROJECT": "p"},
    )

    assert "CREATE TABLE IF NOT EXISTS llm_costs" in db.commands[0][0]
    assert "INSERT INTO llm_costs" in db.commands[1][0]
    assert seen["agent"] == "scanner"


def test_read_daily_totals_transforms_rows():
    db = FakeDB()
    db.rows = [("scanner", "qwen", 1.25), ("alpha", "glm-5", 0.8)]
    now = datetime.now(timezone.utc)

    result = read_daily_cost_totals(db, now=now, lookback_hours=24)

    assert result[0]["agent"] == "scanner"
    assert result[1]["total_usd"] == 0.8
    cutoff = db.commands[-1][1][0]
    assert cutoff == now - timedelta(hours=24)
