"""Execution Tracer — complete execution chain tracing.

Traces the full execution chain: Signal Detection → Decision → Sizing → Execution → Fill,
with latency breakdown for debugging.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.tracing.execution")


@dataclass
class TraceStep:
    """A single step in an execution chain."""
    step_type: str  # "signal", "decision", "sizing", "execution", "fill"
    timestamp: datetime
    agent: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None


@dataclass
class ExecutionChain:
    """Complete trace of an execution from signal to fill."""
    trace_id: str
    symbol: str
    created_at: datetime
    steps: list[TraceStep] = field(default_factory=list)
    completed: bool = False

    @property
    def total_latency_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)

    @property
    def step_latencies(self) -> dict[str, float]:
        return {s.step_type: s.duration_ms for s in self.steps}

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)


class ExecutionTracer:
    """Traces complete execution chains from signal to fill.

    Each trace follows: Signal → Decision → Sizing → Execution → Fill
    with latency measurements at each step.
    """

    def __init__(self, max_traces: int = 10_000) -> None:
        self._traces: dict[str, ExecutionChain] = {}
        self._max_traces = max_traces
        self._step_timers: dict[str, float] = {}

    def start_trace(self, trace_id: str, symbol: str) -> ExecutionChain:
        """Start a new execution trace."""
        chain = ExecutionChain(
            trace_id=trace_id,
            symbol=symbol,
            created_at=datetime.now(timezone.utc),
        )
        self._traces[trace_id] = chain
        self._evict_old()
        return chain

    def start_step(self, trace_id: str, step_type: str) -> None:
        """Start timing a step in the execution chain."""
        key = f"{trace_id}:{step_type}"
        self._step_timers[key] = time.monotonic()

    def end_step(
        self,
        trace_id: str,
        step_type: str,
        *,
        agent: str = "",
        data: dict[str, Any] | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> TraceStep | None:
        """End timing and record a step in the execution chain."""
        chain = self._traces.get(trace_id)
        if chain is None:
            logger.warning("No trace found for %s", trace_id)
            return None

        key = f"{trace_id}:{step_type}"
        start_time = self._step_timers.pop(key, None)
        duration = (time.monotonic() - start_time) * 1000 if start_time else 0.0

        step = TraceStep(
            step_type=step_type,
            timestamp=datetime.now(timezone.utc),
            agent=agent,
            data=data or {},
            duration_ms=round(duration, 2),
            success=success,
            error=error,
        )
        chain.steps.append(step)
        return step

    def complete_trace(self, trace_id: str) -> ExecutionChain | None:
        """Mark a trace as completed."""
        chain = self._traces.get(trace_id)
        if chain is not None:
            chain.completed = True
            logger.info(
                "Trace %s completed: %s, latency=%.1fms, steps=%d",
                trace_id, "SUCCESS" if chain.success else "FAILED",
                chain.total_latency_ms, len(chain.steps),
            )
        return chain

    def trace_execution_chain(self, trace_id: str) -> dict[str, Any] | None:
        """Get the full execution chain for a trace.

        Returns a structured view of the trace including:
        - All steps in the chain
        - Latency breakdown per step
        - Overall status
        """
        chain = self._traces.get(trace_id)
        if chain is None:
            return None

        return {
            "trace_id": trace_id,
            "symbol": chain.symbol,
            "created_at": chain.created_at.isoformat(),
            "completed": chain.completed,
            "success": chain.success,
            "chain": [
                {
                    "step": s.step_type,
                    "agent": s.agent,
                    "timestamp": s.timestamp.isoformat(),
                    "duration_ms": s.duration_ms,
                    "success": s.success,
                    "error": s.error,
                    "data": s.data,
                }
                for s in chain.steps
            ],
            "latency_breakdown": chain.step_latencies,
            "total_latency_ms": chain.total_latency_ms,
        }

    def get_recent_traces(
        self,
        limit: int = 50,
        symbol: str | None = None,
        only_failed: bool = False,
    ) -> list[dict[str, Any]]:
        """Get recent execution traces."""
        traces = list(self._traces.values())
        if symbol:
            traces = [t for t in traces if t.symbol == symbol]
        if only_failed:
            traces = [t for t in traces if not t.success]

        # Sort by creation time, most recent first
        traces.sort(key=lambda t: t.created_at, reverse=True)

        return [
            self.trace_execution_chain(t.trace_id)
            for t in traces[:limit]
            if self.trace_execution_chain(t.trace_id) is not None
        ]

    def get_latency_stats(self) -> dict[str, Any]:
        """Get aggregate latency statistics across all traces."""
        step_latencies: dict[str, list[float]] = {}
        for chain in self._traces.values():
            for step in chain.steps:
                step_latencies.setdefault(step.step_type, []).append(step.duration_ms)

        stats: dict[str, Any] = {}
        for step_type, latencies in step_latencies.items():
            if latencies:
                stats[step_type] = {
                    "count": len(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies), 2),
                    "max_ms": round(max(latencies), 2),
                    "min_ms": round(min(latencies), 2),
                }

        return stats

    def _evict_old(self) -> None:
        """Remove oldest traces if over capacity."""
        if len(self._traces) > self._max_traces:
            sorted_ids = sorted(
                self._traces.keys(),
                key=lambda tid: self._traces[tid].created_at,
            )
            to_remove = sorted_ids[: len(self._traces) - self._max_traces + 1]
            for tid in to_remove:
                del self._traces[tid]
