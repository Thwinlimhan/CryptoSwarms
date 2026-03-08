from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AgentAuditEvent:
    timestamp: datetime
    agent: str
    action: str
    run_id: str
    metadata: dict[str, object]


class AgentAuditLog:
    def __init__(self) -> None:
        self._events: list[AgentAuditEvent] = []

    def append(self, event: AgentAuditEvent) -> None:
        self._events.append(event)

    def query(self, *, agent: str | None = None, run_id: str | None = None) -> list[AgentAuditEvent]:
        out = self._events
        if agent is not None:
            out = [e for e in out if e.agent == agent]
        if run_id is not None:
            out = [e for e in out if e.run_id == run_id]
        return out


@dataclass(frozen=True)
class AlertState:
    budget_breach: bool
    pipeline_halt: bool
    exchange_error_spike: bool


def evaluate_alerts(*, llm_spent_usd: float, llm_budget_usd: float, pipeline_halted: bool, exchange_errors: int) -> AlertState:
    return AlertState(
        budget_breach=llm_spent_usd > llm_budget_usd,
        pipeline_halt=bool(pipeline_halted),
        exchange_error_spike=exchange_errors >= 3,
    )


def build_trace_context(agent: str, run_id: str) -> dict[str, str]:
    return {
        "trace_provider": "langsmith",
        "agent": agent,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
