from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol


class EventPublisher(Protocol):
    def publish(self, channel: str, payload: Dict[str, Any]) -> None:
        ...


class RiskEventLogger(Protocol):
    def log(self, event: Dict[str, Any]) -> None:
        ...


class HeartbeatStore(Protocol):
    def setex(self, key: str, ttl_seconds: int, value: str) -> None: ...


@dataclass
class RiskState:
    drawdown_pct: float
    heat_pct: float


@dataclass(frozen=True)
class CircuitBreakerThresholds:
    l1_drawdown_pct: float = 4.0
    l2_drawdown_pct: float = 6.0
    l3_drawdown_pct: float = 8.0
    l4_drawdown_pct: float = 10.0


class InMemoryRiskEventLogger:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def log(self, event: Dict[str, Any]) -> None:
        self.events.append(event)


class RiskMonitor:
    HEARTBEAT_INTERVAL = timedelta(seconds=60)
    HALT_AFTER_STALE = timedelta(minutes=10)

    def __init__(
        self,
        *,
        event_publisher: EventPublisher,
        risk_event_logger: RiskEventLogger,
        thresholds: Optional[CircuitBreakerThresholds] = None,
        heartbeat_store: Optional[HeartbeatStore] = None,
        heartbeat_ttl_seconds: int = 600,
    ) -> None:
        self.event_publisher = event_publisher
        self.risk_event_logger = risk_event_logger
        self.thresholds = thresholds or CircuitBreakerThresholds()
        self._last_heartbeat: Optional[datetime] = None
        self._halt_active = False
        self._heartbeat_store = heartbeat_store
        self._heartbeat_ttl_seconds = heartbeat_ttl_seconds

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        return self._last_heartbeat

    @property
    def halt_active(self) -> bool:
        return self._halt_active

    def publish_heartbeat(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        self._last_heartbeat = now
        self.event_publisher.publish("risk:heartbeat", {"timestamp": now.isoformat()})

        if self._heartbeat_store is not None:
            try:
                self._heartbeat_store.setex("risk_monitor:heartbeat", self._heartbeat_ttl_seconds, now.isoformat())
            except Exception:
                pass

    def heartbeat_due(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self._last_heartbeat is None:
            return True
        return now - self._last_heartbeat >= self.HEARTBEAT_INTERVAL

    def evaluate(self, *, risk_state: RiskState, now: Optional[datetime] = None) -> Optional[str]:
        now = now or datetime.now(timezone.utc)
        if self._last_heartbeat and now - self._last_heartbeat >= self.HALT_AFTER_STALE:
            return self._trigger_halt(level="L4", reason="stale_heartbeat", now=now)

        return self._evaluate_drawdown(risk_state=risk_state, now=now)

    def _evaluate_drawdown(self, *, risk_state: RiskState, now: datetime) -> Optional[str]:
        drawdown = risk_state.drawdown_pct
        level = None
        if drawdown >= self.thresholds.l4_drawdown_pct:
            level = "L4"
        elif drawdown >= self.thresholds.l3_drawdown_pct:
            level = "L3"
        elif drawdown >= self.thresholds.l2_drawdown_pct:
            level = "L2"
        elif drawdown >= self.thresholds.l1_drawdown_pct:
            level = "L1"

        if level:
            reason = f"drawdown_breach_{level.lower()}"
            return self._trigger_halt(level=level, reason=reason, now=now)
        return None

    def _trigger_halt(self, *, level: str, reason: str, now: datetime) -> str:
        self._halt_active = True
        payload = {
            "level": level,
            "reason": reason,
            "timestamp": now.isoformat(),
        }
        self.event_publisher.publish("execution:halt", payload)
        self.risk_event_logger.log(
            {
                "table": "risk_events",
                "event_type": "execution_halt",
                **payload,
            }
        )
        return reason
