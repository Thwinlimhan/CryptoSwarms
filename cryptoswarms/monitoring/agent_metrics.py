"""Agent Metrics — per-agent performance tracking.

Tracks success rates, latencies, and performance metrics
for each agent to identify problematic agents.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("swarm.monitoring.agent_metrics")


@dataclass
class MetricEntry:
    """A single metric data point."""
    success: bool
    latency_ms: float
    timestamp: datetime
    action: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformanceSummary:
    """Performance summary for a single agent."""
    agent: str
    total_actions: int
    successes: int
    failures: int
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    actions_by_type: dict[str, int]
    last_action_at: datetime | None


class AgentMetrics:
    """Tracks per-agent performance metrics.

    Monitors each agent's actions with success/failure rates
    and latency measurements for performance analysis.
    """

    def __init__(self, max_entries_per_agent: int = 10_000) -> None:
        self._metrics: dict[str, list[MetricEntry]] = defaultdict(list)
        self._max_entries = max_entries_per_agent

    def track_agent_performance(
        self,
        agent: str,
        action: str,
        success: bool,
        latency_ms: float,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record a performance metric for an agent.

        Args:
            agent: Agent identifier.
            action: Action type (e.g., "signal_generation", "order_execution").
            success: Whether the action succeeded.
            latency_ms: Time taken in milliseconds.
            data: Optional additional data.
        """
        entry = MetricEntry(
            success=success,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            action=action,
            data=data or {},
        )
        self._metrics[agent].append(entry)

        # Trim oldest entries
        if len(self._metrics[agent]) > self._max_entries:
            self._metrics[agent] = self._metrics[agent][-self._max_entries:]

        if not success:
            logger.warning(
                "Agent %s action '%s' failed (%.1fms)", agent, action, latency_ms,
            )

    def get_agent_summary(
        self,
        agent: str,
        window_hours: float | None = None,
    ) -> AgentPerformanceSummary:
        """Get performance summary for a specific agent.

        Args:
            agent: Agent identifier.
            window_hours: Only include entries from the last N hours.

        Returns:
            AgentPerformanceSummary with aggregated metrics.
        """
        entries = self._metrics.get(agent, [])
        if window_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            entries = [e for e in entries if e.timestamp >= cutoff]

        total = len(entries)
        if total == 0:
            return AgentPerformanceSummary(
                agent=agent,
                total_actions=0,
                successes=0,
                failures=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                actions_by_type={},
                last_action_at=None,
            )

        successes = sum(1 for e in entries if e.success)
        latencies = sorted(e.latency_ms for e in entries)
        actions_by_type: dict[str, int] = {}
        for e in entries:
            actions_by_type[e.action] = actions_by_type.get(e.action, 0) + 1

        return AgentPerformanceSummary(
            agent=agent,
            total_actions=total,
            successes=successes,
            failures=total - successes,
            success_rate=round(successes / total, 4),
            avg_latency_ms=round(sum(latencies) / total, 2),
            p95_latency_ms=round(latencies[int(total * 0.95)] if total > 0 else 0, 2),
            p99_latency_ms=round(latencies[int(total * 0.99)] if total > 0 else 0, 2),
            actions_by_type=actions_by_type,
            last_action_at=entries[-1].timestamp if entries else None,
        )

    def get_all_agents_summary(
        self, window_hours: float | None = None
    ) -> dict[str, AgentPerformanceSummary]:
        """Get performance summaries for all tracked agents."""
        return {
            agent: self.get_agent_summary(agent, window_hours)
            for agent in self._metrics.keys()
        }

    def get_problematic_agents(
        self,
        min_success_rate: float = 0.9,
        max_avg_latency_ms: float = 5000.0,
        window_hours: float = 1.0,
    ) -> list[AgentPerformanceSummary]:
        """Identify agents performing below thresholds."""
        all_summaries = self.get_all_agents_summary(window_hours)
        problematic = []
        for summary in all_summaries.values():
            if summary.total_actions == 0:
                continue
            if (summary.success_rate < min_success_rate
                    or summary.avg_latency_ms > max_avg_latency_ms):
                problematic.append(summary)
        return problematic

    def reset_agent(self, agent: str) -> None:
        """Clear all metrics for a specific agent."""
        self._metrics.pop(agent, None)

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate monitoring statistics."""
        total_entries = sum(len(v) for v in self._metrics.values())
        return {
            "tracked_agents": len(self._metrics),
            "total_entries": total_entries,
            "agents": list(self._metrics.keys()),
        }


# Singleton instance
_agent_metrics: AgentMetrics | None = None


def get_agent_metrics() -> AgentMetrics:
    """Get the global AgentMetrics singleton."""
    global _agent_metrics
    if _agent_metrics is None:
        _agent_metrics = AgentMetrics()
    return _agent_metrics
