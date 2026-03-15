"""Execution Coordinator — per-symbol locking for order execution.

Ensures that only one order can be in-flight for a given symbol at any time,
preventing conflicting orders and unintended hedges.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger("swarm.execution.coordinator")


@dataclass
class ExecutionRecord:
    """Record of a coordinated execution."""
    symbol: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class ExecutionCoordinator:
    """Coordinates order execution with per-symbol locking.

    Prevents conflicting orders on the same symbol by ensuring
    mutual exclusion during order submission and processing.
    """

    def __init__(self, max_concurrent_symbols: int = 10) -> None:
        self._symbol_locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._max_concurrent = max_concurrent_symbols
        self._active_executions: dict[str, ExecutionRecord] = {}
        self._execution_history: list[ExecutionRecord] = []

    def _get_symbol_lock(self, symbol: str) -> asyncio.Lock:
        """Get or create a lock for a specific symbol."""
        if symbol not in self._symbol_locks:
            self._symbol_locks[symbol] = asyncio.Lock()
        return self._symbol_locks[symbol]

    async def execute_with_lock(
        self,
        symbol: str,
        order_fn: Callable[[], Awaitable[Any]],
        timeout: float = 30.0,
    ) -> Any:
        """Execute an order function with per-symbol locking.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT").
            order_fn: Async callable that performs the order.
            timeout: Maximum time to wait for lock acquisition.

        Returns:
            Result of the order function.

        Raises:
            asyncio.TimeoutError: If lock cannot be acquired within timeout.
            Exception: Any exception from the order function is re-raised.
        """
        lock = self._get_symbol_lock(symbol)
        record = ExecutionRecord(
            symbol=symbol,
            started_at=datetime.now(timezone.utc),
        )

        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            record.error = f"Lock acquisition timeout ({timeout}s) for {symbol}"
            logger.error(record.error)
            self._execution_history.append(record)
            raise

        start_time = time.monotonic()
        self._active_executions[symbol] = record

        try:
            result = await order_fn()
            record.success = True
            record.result = result
            logger.info("Execution completed for %s", symbol)
            return result
        except Exception as exc:
            record.error = str(exc)
            logger.error("Execution failed for %s: %s", symbol, exc)
            raise
        finally:
            record.completed_at = datetime.now(timezone.utc)
            record.duration_ms = (time.monotonic() - start_time) * 1000
            self._active_executions.pop(symbol, None)
            self._execution_history.append(record)
            lock.release()

    @property
    def active_symbols(self) -> list[str]:
        """Symbols currently being executed."""
        return list(self._active_executions.keys())

    @property
    def execution_history(self) -> list[ExecutionRecord]:
        return list(self._execution_history)

    def get_stats(self) -> dict[str, Any]:
        """Return execution statistics."""
        total = len(self._execution_history)
        successes = sum(1 for r in self._execution_history if r.success)
        failures = total - successes
        avg_duration = (
            sum(r.duration_ms for r in self._execution_history) / total
            if total > 0
            else 0.0
        )
        return {
            "total_executions": total,
            "successes": successes,
            "failures": failures,
            "avg_duration_ms": round(avg_duration, 2),
            "active_symbols": self.active_symbols,
        }
