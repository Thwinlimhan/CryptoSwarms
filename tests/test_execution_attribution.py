from datetime import datetime, timezone

import pytest

from agents.execution.execution_agent import BinanceExchangeAdapter, ExecutionAgent, GateCheckError, RiskSnapshot, TradeSignal
from cryptoswarms.trade_attribution import TradeAttribution


class StubPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


class StubConfirmGate:
    def verify(self, token: str, action_record_id: str) -> bool:
        return token == "valid" and bool(action_record_id)


def _signal(now: datetime) -> TradeSignal:
    return TradeSignal(
        signal_id="sig-attr",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        confidence=0.95,
        timestamp=now,
        gate_passed=True,
    )


def _risk(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(heartbeat_ts=now, drawdown_pct=1.0, heat_pct=10.0, halt_active=False)


def test_live_execution_requires_trade_attribution():
    now = datetime.now(timezone.utc)
    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="live"),
        event_publisher=StubPublisher(),
        confirm_gate=StubConfirmGate(),
    )

    with pytest.raises(GateCheckError):
        agent.execute(
            signal=_signal(now),
            risk=_risk(now),
            confirm_token="valid",
            action_record_id="a1",
            stop_loss=59000,
            take_profit=62000,
            entry_price=60000,
            now=now,
        )


def test_live_execution_includes_attribution_payload():
    now = datetime.now(timezone.utc)
    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="live"),
        event_publisher=StubPublisher(),
        confirm_gate=StubConfirmGate(),
    )

    result = agent.execute(
        signal=_signal(now),
        risk=_risk(now),
        confirm_token="valid",
        action_record_id="a2",
        stop_loss=59000,
        take_profit=62000,
        entry_price=60000,
        now=now,
        attribution=TradeAttribution(
            hypothesis_id="h1",
            optimizer_run_id="run1",
            optimizer_candidate_id="cand1",
            research_source="composite",
            strategy_id="phase1-btc-breakout-15m",
        ),
    )

    assert result["status"] == "accepted"
    assert result["attribution"]["optimizer_run_id"] == "run1"
