from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import asyncpg


@dataclass(frozen=True)
class Phase1SummaryRow:
    run_time: datetime
    strategy_id: str
    total_signals: int
    accepted_candidates: int
    rejected_candidates: int
    paper_trades: int
    gross_pnl_usd: float
    llm_cost_usd: float


class RedisStreamSignalSink:
    """Runtime sink that emits signals to Redis Streams."""

    def __init__(self, redis_client: Any, stream_name: str = "research:signals") -> None:
        self._redis = redis_client
        self._stream_name = stream_name

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        event = {"topic": topic, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()}
        self._redis.xadd(self._stream_name, {"event": json.dumps(event)})


class AsyncpgPhase1Store:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    async def ensure_schema(self) -> None:
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phase1_signals (
                    run_time TIMESTAMPTZ NOT NULL,
                    strategy_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    payload JSONB NOT NULL
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phase1_daily_summary (
                    run_time TIMESTAMPTZ NOT NULL,
                    strategy_id TEXT NOT NULL,
                    total_signals INT NOT NULL,
                    accepted_candidates INT NOT NULL,
                    rejected_candidates INT NOT NULL,
                    paper_trades INT NOT NULL,
                    gross_pnl_usd DOUBLE PRECISION NOT NULL,
                    llm_cost_usd DOUBLE PRECISION NOT NULL
                );
                """
            )
        finally:
            await conn.close()

    async def write_signals(self, run_time: datetime, strategy_id: str, signals: list[dict[str, object]]) -> None:
        conn = await asyncpg.connect(self._dsn)
        try:
            for signal in signals:
                await conn.execute(
                    """
                    INSERT INTO phase1_signals(run_time, strategy_id, signal_type, symbol, confidence, payload)
                    VALUES($1, $2, $3, $4, $5, $6::jsonb)
                    """,
                    run_time,
                    strategy_id,
                    str(signal.get("signal_type", "UNKNOWN")),
                    str(signal.get("symbol", "UNKNOWN")),
                    float(signal.get("confidence", 0.0)),
                    json.dumps(signal),
                )
        finally:
            await conn.close()

    async def write_summary(self, row: Phase1SummaryRow) -> None:
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute(
                """
                INSERT INTO phase1_daily_summary(
                    run_time, strategy_id, total_signals, accepted_candidates,
                    rejected_candidates, paper_trades, gross_pnl_usd, llm_cost_usd
                )
                VALUES($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                row.run_time,
                row.strategy_id,
                row.total_signals,
                row.accepted_candidates,
                row.rejected_candidates,
                row.paper_trades,
                row.gross_pnl_usd,
                row.llm_cost_usd,
            )
        finally:
            await conn.close()
