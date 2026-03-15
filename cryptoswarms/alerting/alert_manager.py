"""Alert Manager — configurable alerting system for critical events.

Monitors system metrics and triggers alerts via configurable channels
(log, webhook, etc.) when thresholds are breached.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("swarm.alerting")


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


@dataclass
class Alert:
    """An alert triggered by the system."""
    alert_id: str
    severity: AlertSeverity
    message: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


@dataclass
class AlertRule:
    """A condition-based alerting rule."""
    name: str
    severity: AlertSeverity
    condition_fn: Callable[[dict[str, Any]], bool]
    message_template: str
    cooldown_seconds: float = 300.0  # Don't re-fire within cooldown
    last_fired: datetime | None = None


@dataclass
class SystemMetrics:
    """Metrics snapshot for alert evaluation."""
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    open_positions: int = 0
    portfolio_heat_pct: float = 0.0
    error_rate_1h: float = 0.0
    exchange_errors_1h: int = 0
    max_position_age_hours: float = 0.0
    memory_usage_mb: float = 0.0


class AlertManager:
    """Manages alert rules, evaluation, and notification.

    Checks configurable conditions against system metrics
    and dispatches alerts when thresholds are breached.
    """

    def __init__(
        self,
        alert_handlers: list[Callable[[Alert], Awaitable[None]]] | None = None,
    ) -> None:
        self._rules: list[AlertRule] = []
        self._alert_history: list[Alert] = []
        self._handlers = alert_handlers or []
        self._alert_counter = 0

        # Register default rules
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register the default set of alert rules."""
        self._rules.extend([
            AlertRule(
                name="daily_loss_500",
                severity=AlertSeverity.CRITICAL,
                condition_fn=lambda m: m.get("daily_pnl", 0) < -500,
                message_template="Daily loss exceeds $500: ${daily_pnl:.2f}",
                cooldown_seconds=600,
            ),
            AlertRule(
                name="daily_loss_200",
                severity=AlertSeverity.WARNING,
                condition_fn=lambda m: -500 < m.get("daily_pnl", 0) < -200,
                message_template="Daily loss approaching limits: ${daily_pnl:.2f}",
                cooldown_seconds=300,
            ),
            AlertRule(
                name="high_error_rate",
                severity=AlertSeverity.WARNING,
                condition_fn=lambda m: m.get("error_rate_1h", 0) > 0.05,
                message_template="Error rate above 5%: {error_rate_1h:.1%}",
                cooldown_seconds=300,
            ),
            AlertRule(
                name="exchange_errors",
                severity=AlertSeverity.CRITICAL,
                condition_fn=lambda m: m.get("exchange_errors_1h", 0) > 10,
                message_template="High exchange error count: {exchange_errors_1h}",
                cooldown_seconds=600,
            ),
            AlertRule(
                name="high_portfolio_heat",
                severity=AlertSeverity.WARNING,
                condition_fn=lambda m: m.get("portfolio_heat_pct", 0) > 15.0,
                message_template="Portfolio heat above 15%: {portfolio_heat_pct:.1f}%",
                cooldown_seconds=300,
            ),
            AlertRule(
                name="stale_position",
                severity=AlertSeverity.INFO,
                condition_fn=lambda m: m.get("max_position_age_hours", 0) > 48,
                message_template="Position held over 48h: {max_position_age_hours:.1f}h",
                cooldown_seconds=3600,
            ),
        ])

    def add_rule(self, rule: AlertRule) -> None:
        """Add a custom alerting rule."""
        self._rules.append(rule)

    async def check_alert_conditions(
        self, metrics: SystemMetrics | dict[str, Any]
    ) -> list[Alert]:
        """Evaluate all rules against current metrics.

        Args:
            metrics: SystemMetrics or dict of metric values.

        Returns:
            List of triggered alerts.
        """
        if isinstance(metrics, SystemMetrics):
            metrics_dict: dict[str, Any] = {
                "daily_pnl": metrics.daily_pnl,
                "total_pnl": metrics.total_pnl,
                "open_positions": metrics.open_positions,
                "portfolio_heat_pct": metrics.portfolio_heat_pct,
                "error_rate_1h": metrics.error_rate_1h,
                "exchange_errors_1h": metrics.exchange_errors_1h,
                "max_position_age_hours": metrics.max_position_age_hours,
                "memory_usage_mb": metrics.memory_usage_mb,
            }
        else:
            metrics_dict = dict(metrics)

        now = datetime.now(timezone.utc)
        triggered: list[Alert] = []

        for rule in self._rules:
            # Check cooldown
            if rule.last_fired is not None:
                elapsed = (now - rule.last_fired).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue

            try:
                if rule.condition_fn(metrics_dict):
                    self._alert_counter += 1
                    alert = Alert(
                        alert_id=f"alert_{self._alert_counter:06d}",
                        severity=rule.severity,
                        message=rule.message_template.format(**metrics_dict),
                        source=rule.name,
                        data=metrics_dict,
                    )
                    rule.last_fired = now
                    triggered.append(alert)
                    self._alert_history.append(alert)

                    # Dispatch to handlers
                    await self._dispatch_alert(alert)

                    logger.log(
                        logging.CRITICAL if rule.severity == AlertSeverity.EMERGENCY
                        else logging.WARNING,
                        "[%s] %s: %s",
                        alert.severity.value, rule.name, alert.message,
                    )
            except Exception as exc:
                logger.error("Error evaluating rule '%s': %s", rule.name, exc)

        # Keep history bounded
        if len(self._alert_history) > 10_000:
            self._alert_history = self._alert_history[-10_000:]

        return triggered

    async def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all registered handlers."""
        for handler in self._handlers:
            try:
                await handler(alert)
            except Exception as exc:
                logger.error("Alert handler failed: %s", exc)

    def get_recent_alerts(
        self,
        severity: AlertSeverity | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        """Get recent alerts, optionally filtered by severity."""
        alerts = self._alert_history
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Return alerting statistics."""
        by_severity: dict[str, int] = {}
        for alert in self._alert_history:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        return {
            "total_alerts": len(self._alert_history),
            "by_severity": by_severity,
            "unacknowledged": sum(1 for a in self._alert_history if not a.acknowledged),
            "rules_count": len(self._rules),
        }
