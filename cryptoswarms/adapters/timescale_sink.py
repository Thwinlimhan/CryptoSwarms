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
            logger.info("TimescaleSink connected to %s", self._dsn.split("@")[-1] if "@" in self._dsn else "***")
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

    async def write_decision(self, record: dict[str, Any]) -> bool:
        """Write a new pending decision."""
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO decisions (id, label, strategy_id, symbol, ev_estimate, win_probability, position_size_usd, bias_flags, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                record.get("id"),
                record.get("label"),
                record.get("strategy_id"),
                record.get("symbol"),
                record.get("ev_estimate"),
                record.get("win_probability"),
                record.get("position_size_usd"),
                json.dumps(record.get("bias_flags", [])),
                record.get("status", "pending")
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write decision: %s", exc)
            return False

    async def resolve_decision(self, decision_id: str, status: str, pnl: float, notes: str = "") -> bool:
        """Update an existing decision with outcome."""
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                UPDATE decisions
                SET status = $2, pnl_usd = $3, notes = $4, resolved_at = NOW()
                WHERE id = $1
                """,
                decision_id,
                status,
                pnl,
                notes
            )
            return True
        except Exception as exc:
            logger.warning("Failed to resolve decision: %s", exc)
            return False

    async def write_research_experiment(self, record: dict[str, Any]) -> bool:
        """Write a research experiment result."""
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO research_experiments (theme, variable, baseline_value, variant_value, score, delta_vs_baseline, metrics, status, log)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                record.get("theme"),
                record.get("variable"),
                record.get("baseline_value"),
                record.get("variant_value"),
                record.get("score"),
                record.get("delta_vs_baseline"),
                json.dumps(record.get("metrics", {})),
                record.get("status", "completed"),
                record.get("log")
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write research experiment: %s", exc)
            return False

    async def write_research_report(self, record: dict[str, Any]) -> bool:
        """Write a daily research report."""
        if not self._pool:
            return False
        try:
            await self._pool.execute(
                """
                INSERT INTO research_reports (date, theme, data_source, summary, recommendation, regressions, safety_note, full_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                record.get("date"),
                record.get("theme"),
                record.get("data_source"),
                record.get("summary"),
                record.get("recommendation"),
                record.get("regressions"),
                record.get("safety_note"),
                json.dumps(record.get("full_data", {}))
            )
            return True
        except Exception as exc:
            logger.warning("Failed to write research report: %s", exc)
            return False
    async def get_recent_signals(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent signals for analysis."""
        if not self._pool:
            return []
        try:
            rows = await self._pool.fetch(
                "SELECT * FROM signals ORDER BY time DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Failed to fetch signals: %s", exc)
            return []

    async def get_recent_decisions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent decisions for analysis."""
        if not self._pool:
            return []
        try:
            rows = await self._pool.fetch(
                "SELECT * FROM decisions ORDER BY time DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Failed to fetch decisions: %s", exc)
            return []
    async def get_recent_experiments(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch recent research experiments."""
        if not self._pool:
            return []
        try:
            rows = await self._pool.fetch(
                "SELECT * FROM research_experiments ORDER BY time DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Failed to fetch experiments: %s", exc)
            return []

    async def get_recent_reports(self, limit: int = 1) -> list[dict[str, Any]]:
        """Fetch recent research reports."""
        if not self._pool:
            return []
        try:
            rows = await self._pool.fetch(
                "SELECT * FROM research_reports ORDER BY time DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Failed to fetch reports: %s", exc)
            return []
