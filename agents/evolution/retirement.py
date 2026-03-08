from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SqlExecutor(Protocol):
    def fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]: ...

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None: ...


class Publisher(Protocol):
    def publish(self, channel: str, payload: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class RetirementDecision:
    strategy_id: str
    retired: bool
    reason: str


def evaluate_retirement(sharpe_90d: float, threshold: float = 0.5) -> tuple[bool, str]:
    if sharpe_90d < threshold:
        return True, f"90d sharpe below threshold ({sharpe_90d:.3f} < {threshold:.3f})"
    return False, "healthy"


def retire_underperformers(db: SqlExecutor, publisher: Publisher, threshold: float = 0.5) -> list[RetirementDecision]:
    rows = db.fetchall(
        "SELECT strategy_id, sharpe_90d FROM strategy_health WHERE active = TRUE",
        (),
    )

    decisions: list[RetirementDecision] = []
    for strategy_id, sharpe_90d in rows:
        retired, reason = evaluate_retirement(float(sharpe_90d), threshold)
        decision = RetirementDecision(strategy_id=str(strategy_id), retired=retired, reason=reason)
        decisions.append(decision)

        if retired:
            db.execute("UPDATE strategy_health SET active = FALSE WHERE strategy_id = %s", (decision.strategy_id,))
            publisher.publish(
                "evolution:retire",
                {"strategy_id": decision.strategy_id, "reason": decision.reason},
            )

    return decisions
