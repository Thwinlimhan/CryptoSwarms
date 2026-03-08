from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class SqlExecutor(Protocol):
    def fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]: ...


class Publisher(Protocol):
    def publish(self, channel: str, payload: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class DailyPerformanceReport:
    date: str
    daily_pnl_usd: float
    best_strategy: str
    worst_strategy: str
    llm_cost_usd: float


def generate_daily_report(db: SqlExecutor, now: datetime | None = None) -> DailyPerformanceReport:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    since = now - timedelta(hours=24)

    trades = db.fetchall(
        "SELECT strategy_id, COALESCE(SUM(realised_pnl), 0) FROM trades WHERE time > %s GROUP BY strategy_id",
        (since,),
    )
    costs = db.fetchall(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_costs WHERE time > %s",
        (since,),
    )

    if trades:
        ordered = sorted(((str(r[0]), float(r[1])) for r in trades), key=lambda x: x[1], reverse=True)
        best = ordered[0]
        worst = ordered[-1]
        total = sum(v for _, v in ordered)
    else:
        best = ("none", 0.0)
        worst = ("none", 0.0)
        total = 0.0

    llm_cost = float(costs[0][0]) if costs else 0.0

    return DailyPerformanceReport(
        date=now.date().isoformat(),
        daily_pnl_usd=round(total, 4),
        best_strategy=best[0],
        worst_strategy=worst[0],
        llm_cost_usd=round(llm_cost, 4),
    )


def publish_daily_report(report: DailyPerformanceReport, publisher: Publisher) -> None:
    payload = {
        "date": report.date,
        "daily_pnl_usd": report.daily_pnl_usd,
        "best_strategy": report.best_strategy,
        "worst_strategy": report.worst_strategy,
        "llm_cost_usd": report.llm_cost_usd,
    }
    publisher.publish("redis:evolution:daily_report", payload)
    publisher.publish("mission-control:daily_report", payload)
