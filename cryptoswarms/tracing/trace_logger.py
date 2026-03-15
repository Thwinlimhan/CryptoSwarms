"""Trace Logger — structured logging with trace IDs for full execution audit trail.

Provides consistent, structured log entries across all swarm components,
enabling end-to-end tracing from signal detection through order execution.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.tracing")


def new_trace_id() -> str:
    """Generate a new unique trace ID."""
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class TraceEvent:
    """A single event in a traced execution chain."""
    trace_id: str
    event_type: str
    agent: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    parent_event_id: str | None = None
    duration_ms: float | None = None


class TraceLogger:
    """Structured logger with trace IDs for full audit trail.

    All decisions, signals, orders, and fills are logged with
    a common trace_id for end-to-end correlation.
    """

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        self._max_events = 100_000  # Prevent unbounded growth

    def log_decision(self, trace_id: str, **kwargs: Any) -> TraceEvent:
        """Log a trading decision event."""
        event = TraceEvent(
            trace_id=trace_id,
            event_type="DECISION",
            agent=str(kwargs.get("agent", "unknown")),
            timestamp=datetime.now(timezone.utc),
            data={k: v for k, v in kwargs.items() if k != "agent"},
        )
        self._append(event)
        logger.info(
            "DECISION",
            extra={
                "trace_id": trace_id,
                "timestamp": event.timestamp.isoformat(),
                **kwargs,
            },
        )
        return event

    def log_signal(self, trace_id: str, **kwargs: Any) -> TraceEvent:
        """Log a signal detection event."""
        event = TraceEvent(
            trace_id=trace_id,
            event_type="SIGNAL",
            agent=str(kwargs.get("agent", "unknown")),
            timestamp=datetime.now(timezone.utc),
            data={k: v for k, v in kwargs.items() if k != "agent"},
        )
        self._append(event)
        logger.info(
            "SIGNAL",
            extra={
                "trace_id": trace_id,
                "timestamp": event.timestamp.isoformat(),
                **kwargs,
            },
        )
        return event

    def log_order(self, trace_id: str, **kwargs: Any) -> TraceEvent:
        """Log an order submission event."""
        event = TraceEvent(
            trace_id=trace_id,
            event_type="ORDER",
            agent=str(kwargs.get("agent", "execution")),
            timestamp=datetime.now(timezone.utc),
            data={k: v for k, v in kwargs.items() if k != "agent"},
        )
        self._append(event)
        logger.info(
            "ORDER",
            extra={
                "trace_id": trace_id,
                "timestamp": event.timestamp.isoformat(),
                **kwargs,
            },
        )
        return event

    def log_fill(self, trace_id: str, **kwargs: Any) -> TraceEvent:
        """Log an order fill event."""
        event = TraceEvent(
            trace_id=trace_id,
            event_type="FILL",
            agent=str(kwargs.get("agent", "execution")),
            timestamp=datetime.now(timezone.utc),
            data={k: v for k, v in kwargs.items() if k != "agent"},
        )
        self._append(event)
        logger.info(
            "FILL",
            extra={
                "trace_id": trace_id,
                "timestamp": event.timestamp.isoformat(),
                **kwargs,
            },
        )
        return event

    def log_error(self, trace_id: str, **kwargs: Any) -> TraceEvent:
        """Log an error event."""
        event = TraceEvent(
            trace_id=trace_id,
            event_type="ERROR",
            agent=str(kwargs.get("agent", "unknown")),
            timestamp=datetime.now(timezone.utc),
            data={k: v for k, v in kwargs.items() if k != "agent"},
        )
        self._append(event)
        logger.error(
            "ERROR",
            extra={
                "trace_id": trace_id,
                "timestamp": event.timestamp.isoformat(),
                **kwargs,
            },
        )
        return event

    def get_trace(self, trace_id: str) -> list[TraceEvent]:
        """Get all events for a specific trace."""
        return [e for e in self._events if e.trace_id == trace_id]

    def get_recent_events(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[TraceEvent]:
        """Get recent events, optionally filtered by type."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def _append(self, event: TraceEvent) -> None:
        """Append event to the log, trimming if at max capacity."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            # Keep the most recent 80% of events
            trim_to = int(self._max_events * 0.8)
            self._events = self._events[-trim_to:]

    def export_json(self) -> str:
        """Export all events as JSON string."""
        return json.dumps(
            [
                {
                    "trace_id": e.trace_id,
                    "event_type": e.event_type,
                    "agent": e.agent,
                    "timestamp": e.timestamp.isoformat(),
                    "data": e.data,
                    "duration_ms": e.duration_ms,
                }
                for e in self._events
            ],
            indent=2,
        )


# Singleton instance
_trace_logger: TraceLogger | None = None


def get_trace_logger() -> TraceLogger:
    """Get the global TraceLogger singleton."""
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = TraceLogger()
    return _trace_logger
