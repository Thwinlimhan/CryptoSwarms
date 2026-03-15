"""Predictive Alerter — ML-based predictive risk alerting.

Uses simple heuristic/statistical models to predict potential
risk events before they occur, enabling proactive intervention.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.analytics.predictive")


@dataclass(frozen=True)
class PredictiveAlert:
    """A predicted risk event."""
    alert_type: str
    risk_score: float  # 0.0 to 1.0
    predicted_event: str
    confidence: float
    time_horizon_minutes: float
    recommended_action: str
    details: dict[str, Any]


class PredictiveAlerter:
    """Predicts potential risk events using statistical models.

    Uses rolling statistics and trend detection to identify
    emerging risk patterns before they become critical.
    """

    def __init__(
        self,
        alert_threshold: float = 0.7,
        history_window: int = 100,
    ) -> None:
        self.alert_threshold = alert_threshold
        self.history_window = history_window
        self._metrics_history: list[dict[str, Any]] = []
        self._alert_history: list[PredictiveAlert] = []

    def ingest_metrics(self, metrics: dict[str, Any]) -> None:
        """Add a metrics snapshot to the history."""
        self._metrics_history.append({
            **metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._metrics_history) > self.history_window:
            self._metrics_history = self._metrics_history[-self.history_window:]

    def predict_risk_events(
        self, current_metrics: dict[str, Any],
    ) -> list[PredictiveAlert]:
        """Analyze current and historical metrics to predict risk events.

        Args:
            current_metrics: Current system metrics snapshot.

        Returns:
            List of predicted risk alerts.
        """
        self.ingest_metrics(current_metrics)
        alerts: list[PredictiveAlert] = []

        # Check various risk predictors
        alerts.extend(self._predict_drawdown_risk(current_metrics))
        alerts.extend(self._predict_volatility_spike(current_metrics))
        alerts.extend(self._predict_error_cascade(current_metrics))
        alerts.extend(self._predict_liquidity_risk(current_metrics))

        # Filter by threshold
        significant = [a for a in alerts if a.risk_score >= self.alert_threshold]
        self._alert_history.extend(significant)

        if significant:
            logger.warning(
                "Predictive alerts: %d events predicted above threshold %.2f",
                len(significant), self.alert_threshold,
            )

        return significant

    def _predict_drawdown_risk(
        self, metrics: dict[str, Any],
    ) -> list[PredictiveAlert]:
        """Predict if drawdown is likely to worsen."""
        alerts: list[PredictiveAlert] = []
        daily_pnl = metrics.get("daily_pnl", 0.0)
        pnl_history = [m.get("daily_pnl", 0.0) for m in self._metrics_history]

        if len(pnl_history) < 5:
            return alerts

        # Check if PnL is trending negative
        recent = pnl_history[-5:]
        trend = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])

        if trend >= 3 and daily_pnl < 0:
            risk_score = min(1.0, abs(daily_pnl) / 200 + trend * 0.15)
            alerts.append(PredictiveAlert(
                alert_type="DRAWDOWN_PREDICTION",
                risk_score=round(risk_score, 3),
                predicted_event="Drawdown likely to continue or worsen",
                confidence=round(trend / 5, 2),
                time_horizon_minutes=60,
                recommended_action="Reduce position sizes or halt new entries",
                details={"daily_pnl": daily_pnl, "negative_trend_count": trend},
            ))

        return alerts

    def _predict_volatility_spike(
        self, metrics: dict[str, Any],
    ) -> list[PredictiveAlert]:
        """Predict upcoming volatility spikes."""
        alerts: list[PredictiveAlert] = []
        volatility = metrics.get("market_volatility", 0.0)
        vol_history = [m.get("market_volatility", 0.0) for m in self._metrics_history]

        if len(vol_history) < 10 or volatility == 0:
            return alerts

        avg_vol = sum(vol_history) / len(vol_history)
        if avg_vol == 0:
            return alerts

        vol_ratio = volatility / avg_vol

        if vol_ratio > 1.5:
            risk_score = min(1.0, vol_ratio / 3.0)
            alerts.append(PredictiveAlert(
                alert_type="VOLATILITY_SPIKE",
                risk_score=round(risk_score, 3),
                predicted_event="Elevated volatility detected, spike possible",
                confidence=round(min(1.0, vol_ratio / 2), 2),
                time_horizon_minutes=30,
                recommended_action="Tighten stop-losses and reduce position sizes",
                details={
                    "current_vol": volatility,
                    "avg_vol": round(avg_vol, 4),
                    "vol_ratio": round(vol_ratio, 2),
                },
            ))

        return alerts

    def _predict_error_cascade(
        self, metrics: dict[str, Any],
    ) -> list[PredictiveAlert]:
        """Predict potential error cascades."""
        alerts: list[PredictiveAlert] = []
        error_rate = metrics.get("error_rate_1h", 0.0)
        error_history = [m.get("error_rate_1h", 0.0) for m in self._metrics_history]

        if len(error_history) < 5:
            return alerts

        # Check for accelerating errors
        recent = error_history[-5:]
        increasing = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])

        if increasing >= 3 and error_rate > 0.02:
            risk_score = min(1.0, error_rate * 10 + increasing * 0.1)
            alerts.append(PredictiveAlert(
                alert_type="ERROR_CASCADE",
                risk_score=round(risk_score, 3),
                predicted_event="Error rate accelerating, cascade possible",
                confidence=round(increasing / 5, 2),
                time_horizon_minutes=15,
                recommended_action="Investigate root cause, consider circuit break",
                details={
                    "error_rate": error_rate,
                    "trend": "accelerating",
                    "increase_count": increasing,
                },
            ))

        return alerts

    def _predict_liquidity_risk(
        self, metrics: dict[str, Any],
    ) -> list[PredictiveAlert]:
        """Predict liquidity risk from position concentration."""
        alerts: list[PredictiveAlert] = []
        portfolio_heat = metrics.get("portfolio_heat_pct", 0.0)
        open_positions = metrics.get("open_positions", 0)

        if portfolio_heat > 12 and open_positions > 5:
            risk_score = min(1.0, portfolio_heat / 20 + open_positions * 0.03)
            alerts.append(PredictiveAlert(
                alert_type="LIQUIDITY_RISK",
                risk_score=round(risk_score, 3),
                predicted_event="High portfolio heat may cause liquidity issues on exit",
                confidence=0.6,
                time_horizon_minutes=120,
                recommended_action="Reduce least-performing positions gradually",
                details={
                    "portfolio_heat_pct": portfolio_heat,
                    "open_positions": open_positions,
                },
            ))

        return alerts

    def get_recent_predictions(self, limit: int = 20) -> list[PredictiveAlert]:
        """Get recent predictive alerts."""
        return self._alert_history[-limit:]
