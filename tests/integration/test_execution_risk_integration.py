from datetime import datetime, timedelta, timezone

import pytest

from agents.execution.execution_agent import (
    BinanceExchangeAdapter,
    ExecutionAgent,
    GateCheckError,
    RiskSnapshot,
    TradeSignal,
)
from agents.execution.risk_monitor import InMemoryRiskEventLogger, RiskMonitor, RiskState


class StubPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


class StubConfirmGate:
    def verify(self, token: str, action_record_id: str) -> bool:
        return token == "valid" and bool(action_record_id)


def make_signal(now: datetime) -> TradeSignal:
    return TradeSignal(
        signal_id="sig-1",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        confidence=0.9,
        timestamp=now,
        gate_passed=True,
    )


def test_execution_blocked_when_heartbeat_stale() -> None:
    now = datetime.now(timezone.utc)
    publisher = StubPublisher()
    monitor = RiskMonitor(event_publisher=publisher, risk_event_logger=InMemoryRiskEventLogger())

    monitor.publish_heartbeat(now - timedelta(minutes=11))
    reason = monitor.evaluate(risk_state=RiskState(drawdown_pct=1.0, heat_pct=10.0), now=now)
    assert reason == "stale_heartbeat"
    assert monitor.halt_active is True

    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="paper"),
        event_publisher=publisher,
        confirm_gate=StubConfirmGate(),
    )

    risk_snapshot = RiskSnapshot(
        heartbeat_ts=now - timedelta(minutes=11),
        drawdown_pct=1.0,
        heat_pct=10.0,
        halt_active=monitor.halt_active,
    )

    with pytest.raises(GateCheckError):
        agent.execute(
            signal=make_signal(now),
            risk=risk_snapshot,
            confirm_token="valid",
            action_record_id="action-1",
            stop_loss=59000,
            take_profit=63000,
            now=now,
        )


def test_execution_blocked_when_drawdown_breach() -> None:
    now = datetime.now(timezone.utc)
    publisher = StubPublisher()
    risk_logger = InMemoryRiskEventLogger()
    monitor = RiskMonitor(event_publisher=publisher, risk_event_logger=risk_logger)

    monitor.publish_heartbeat(now)
    reason = monitor.evaluate(risk_state=RiskState(drawdown_pct=10.5, heat_pct=10.0), now=now)
    assert reason == "drawdown_breach_l4"

    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="paper"),
        event_publisher=publisher,
        confirm_gate=StubConfirmGate(),
    )

    risk_snapshot = RiskSnapshot(
        heartbeat_ts=now,
        drawdown_pct=10.5,
        heat_pct=10.0,
        halt_active=monitor.halt_active,
    )

    with pytest.raises(GateCheckError):
        agent.execute(
            signal=make_signal(now),
            risk=risk_snapshot,
            confirm_token="valid",
            action_record_id="action-2",
            stop_loss=59000,
            take_profit=63000,
            now=now,
        )

    assert any(channel == "execution:halt" for channel, _ in publisher.events)
    assert risk_logger.events and risk_logger.events[-1]["table"] == "risk_events"
