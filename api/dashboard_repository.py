from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

from cryptoswarms.dashboard_insights import DashboardInsightInput
from cryptoswarms.trade_attribution import extract_trade_trace
from api.settings import settings

try:
    from redis.asyncio import from_url as redis_from_url
except ImportError:
    class _NullRedisClient:
        async def ping(self) -> bool:
            return False

        async def get(self, key: str) -> str | None:
            _ = key
            return None

        async def aclose(self) -> None:
            return None

    def redis_from_url(*args: object, **kwargs: object) -> _NullRedisClient:
        _ = (args, kwargs)
        return _NullRedisClient()


def _parse_heartbeat(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except Exception:
        return None


def _timescale_dsn() -> str:
    return (
        f"postgresql://{settings.timescaledb_user}:{settings.timescaledb_password}"
        f"@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    )


class DashboardRepository:
    def __init__(self, registered_agents: list[str]) -> None:
        self.registered_agents = registered_agents

    async def fetch_redis_heartbeats(self) -> dict[str, datetime | None]:
        data: dict[str, datetime | None] = {name: None for name in self.registered_agents}
        try:
            client = redis_from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            for name in self.registered_agents:
                raw = await client.get(f"heartbeat:{name}")
                data[name] = _parse_heartbeat(raw)
            await client.aclose()
        except Exception:
            pass
        return data

    async def fetch_signal_counts(self) -> dict[str, int]:
        counts = {name: 0 for name in self.registered_agents}
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                rows = await conn.fetch(
                    """
                    SELECT agent_name, COUNT(*) AS c
                    FROM signals
                    WHERE time >= date_trunc('day', now())
                      AND agent_name = ANY($1::text[])
                    GROUP BY agent_name
                    """,
                    self.registered_agents,
                )
                for row in rows:
                    counts[str(row["agent_name"])] = int(row["c"])
            finally:
                await conn.close()
        except Exception:
            pass
        return counts

    async def fetch_equity_curve(self, lookback_hours: int = 168) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                rows = await conn.fetch(
                    """
                    SELECT time, SUM(COALESCE(realised_pnl, 0)) OVER (ORDER BY time) AS equity_usd
                    FROM trades
                    WHERE mode = 'live'
                      AND time >= $1
                    ORDER BY time
                    LIMIT 500
                    """,
                    since,
                )
                if rows:
                    return [{"time": r["time"].isoformat(), "equity_usd": float(r["equity_usd"] or 0.0)} for r in rows]
            finally:
                await conn.close()
        except Exception:
            pass
        return []

    async def fetch_current_regime(self) -> dict[str, Any]:
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                row = await conn.fetchrow(
                    """
                    SELECT regime, confidence
                    FROM regimes
                    ORDER BY time DESC
                    LIMIT 1
                    """
                )
                if row:
                    return {
                        "regime": str(row["regime"]),
                        "confidence": float(row["confidence"] or 0.0),
                        "strategy_allocation": {"phase1-btc-breakout-15m": 1.0},
                    }
            finally:
                await conn.close()
        except Exception:
            pass

        return {
            "regime": "unknown",
            "confidence": 0.0,
            "strategy_allocation": {},
        }

    async def fetch_pending_validation(self) -> list[dict[str, Any]]:
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                rows = await conn.fetch(
                    """
                    SELECT strategy_id, gate, passed, time
                    FROM validations
                    ORDER BY time DESC
                    LIMIT 200
                    """
                )
                out = []
                for r in rows:
                    stage = str(r["gate"] or "queued")
                    out.append(
                        {
                            "strategy_id": str(r["strategy_id"]),
                            "stage": stage,
                            "status": "pass" if bool(r["passed"]) else "fail",
                            "time": r["time"].isoformat() if r["time"] else None,
                        }
                    )
                return out
            finally:
                await conn.close()
        except Exception:
            return []

    async def fetch_latest_risk_event(self) -> dict[str, Any] | None:
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                row = await conn.fetchrow(
                    """
                    SELECT time, level, trigger, portfolio_heat, daily_dd
                    FROM risk_events
                    ORDER BY time DESC
                    LIMIT 1
                    """
                )
                if row:
                    return {
                        "time": row["time"],
                        "level": int(row["level"] or 0),
                        "trigger": str(row["trigger"] or "none"),
                        "portfolio_heat": float(row["portfolio_heat"] or 0.0),
                        "daily_dd": float(row["daily_dd"] or 0.0),
                    }
            finally:
                await conn.close()
        except Exception:
            pass
        return None

    async def fetch_dashboard_insight_inputs(self, lookback_hours: int) -> DashboardInsightInput:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
        trade_rows: list[dict[str, object]] = []
        validation_rows: list[dict[str, object]] = []
        signal_rows: list[dict[str, object]] = []
        attribution_rows: list[dict[str, object]] = []

        try:
            conn = await asyncpg.connect(_timescale_dsn())
            try:
                trades = await conn.fetch(
                    """
                    SELECT realised_pnl, slippage_bps, id, strategy_id, metadata
                    FROM trades
                    WHERE mode = 'live' AND time >= $1
                    ORDER BY time ASC
                    LIMIT 2000
                    """,
                    since,
                )
                trade_rows = [{"realised_pnl": row["realised_pnl"], "slippage_bps": row["slippage_bps"]} for row in trades]
                attribution_rows = [extract_trade_trace(dict(row)) for row in trades]

                validations = await conn.fetch(
                    """
                    SELECT passed
                    FROM validations
                    WHERE time >= $1
                    ORDER BY time DESC
                    LIMIT 2000
                    """,
                    since,
                )
                validation_rows = [dict(row) for row in validations]

                signals = await conn.fetch(
                    """
                    SELECT confidence, acted_on
                    FROM signals
                    WHERE time >= $1
                    ORDER BY time DESC
                    LIMIT 2000
                    """,
                    since,
                )
                signal_rows = [dict(row) for row in signals]
            finally:
                await conn.close()
        except Exception:
            pass

        regime = await self.fetch_current_regime()
        risk_event = await self.fetch_latest_risk_event()
        return DashboardInsightInput(
            trade_rows=trade_rows,
            validation_rows=validation_rows,
            signal_rows=signal_rows,
            attribution_rows=attribution_rows,
            regime=regime,
            risk_event=risk_event,
        )

    async def fetch_live_trade_traces(self, limit: int = 500, strategy_id: str | None = None) -> list[dict[str, str | None]]:
        max_limit = max(1, min(int(limit), 2000))
        traces: list[dict[str, str | None]] = []
        try:
            conn = await asyncpg.connect(_timescale_dsn(), timeout=2.0)
            try:
                if strategy_id:
                    rows = await conn.fetch(
                        """
                        SELECT id, strategy_id, metadata
                        FROM trades
                        WHERE mode = 'live' AND strategy_id = $1
                        ORDER BY time DESC
                        LIMIT $2
                        """,
                        strategy_id,
                        max_limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, strategy_id, metadata
                        FROM trades
                        WHERE mode = 'live'
                        ORDER BY time DESC
                        LIMIT $1
                        """,
                        max_limit,
                    )
                traces = [extract_trade_trace(dict(row)) for row in rows]
            finally:
                await conn.close()
        except Exception:
            pass
        return traces
