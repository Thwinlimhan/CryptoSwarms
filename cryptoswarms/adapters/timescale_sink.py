"""Async signal and data writer for TimescaleDB.

Writes signals, regime classifications, and candle data
to the existing TimescaleDB schema.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class TimescaleSink:
    """Writes agent output to TimescaleDB tables."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5, timeout=5.0)
            logger.info("TimescaleSink connected to %s", self._dsn.split("@")[-1])
        except Exception as exc:
            logger.warning("TimescaleSink could not connect: %s", exc)
            self._pool = None

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def write_signal(
        self,
        *,
        agent_name: str,
        signal_type: str,
        symbol: str,
        confidence: float,
        acted_on: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO signals (agent_name, signal_type, symbol, confidence, acted_on, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                agent_name,
                signal_type,
                symbol,
                confidence,
                acted_on,
                json.dumps(metadata or {}),
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write signal: %s", exc)
            return False

    async def write_regime(
        self,
        *,
        regime: str,
        confidence: float,
        indicators: dict[str, Any] | None = None,
    ) -> bool:
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO regimes (regime, confidence, indicators)
                VALUES ($1, $2, $3)
                """,
                regime,
                confidence,
                json.dumps(indicators or {}),
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write regime: %s", exc)
            return False

    async def write_risk_event(
        self,
        *,
        level: int,
        trigger: str,
        portfolio_heat: float = 0.0,
        daily_dd: float = 0.0,
    ) -> bool:
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO risk_events (level, trigger, portfolio_heat, daily_dd)
                VALUES ($1, $2, $3, $4)
                """,
                level,
                trigger,
                portfolio_heat,
                daily_dd,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write risk event: %s", exc)
            return False

    async def write_llm_cost(
        self,
        *,
        agent: str,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> bool:
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO llm_costs (agent, model, tokens_in, tokens_out, cost_usd)
                VALUES ($1, $2, $3, $4, $5)
                """,
                agent,
                model,
                tokens_in,
                tokens_out,
                cost_usd,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write LLM cost: %s", exc)
            return False
