from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from cryptoswarms.tracing import LlmTraceEvent, emit_langsmith_trace


class SqlExecutor(Protocol):
    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None: ...

    def fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]: ...


@dataclass(frozen=True)
class LlmCostEvent:
    timestamp: datetime
    agent: str
    model: str
    cost_usd: float


def costs_schema_sql() -> str:
    return """
CREATE TABLE IF NOT EXISTS llm_costs (
    time TIMESTAMPTZ NOT NULL,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    cost_usd DOUBLE PRECISION NOT NULL CHECK (cost_usd >= 0)
);
""".strip()


def ensure_costs_schema(db: SqlExecutor) -> None:
    db.execute(costs_schema_sql())


def write_llm_cost(db: SqlExecutor, event: LlmCostEvent, trace_env: dict[str, str] | None = None) -> None:
    ts = event.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    db.execute(
        "INSERT INTO llm_costs(time, agent, model, cost_usd) VALUES (%s, %s, %s, %s)",
        (ts, event.agent, event.model, float(event.cost_usd)),
    )

    emit_langsmith_trace(
        LlmTraceEvent(
            time=ts,
            agent=event.agent,
            model=event.model,
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=float(event.cost_usd),
            metadata={"source": "llm_costs"},
        ),
        env=trace_env or dict(os.environ),
    )


def read_daily_cost_totals(db: SqlExecutor, now: datetime, lookback_hours: int = 24) -> list[dict[str, object]]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    window_start = now - timedelta(hours=lookback_hours)
    rows = db.fetchall(
        """
SELECT agent, model, SUM(cost_usd) AS total_usd
FROM llm_costs
WHERE time > %s
GROUP BY agent, model
ORDER BY total_usd DESC
""".strip(),
        (window_start,),
    )
    return [{"agent": r[0], "model": r[1], "total_usd": float(r[2])} for r in rows]
