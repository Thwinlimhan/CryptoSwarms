from datetime import datetime, timezone

import pytest

from agents.execution.execution_agent import (
    BinanceExchangeAdapter,
    ExecutionAgent,
    ExecutionConfig,
    GateCheckError,
    RiskSnapshot,
    TradeSignal,
)
from cryptoswarms.paperclip_runtime import PaperclipRuntimeGuard


class StubPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


class StubConfirmGate:
    def verify(self, token: str, action_record_id: str) -> bool:
        return token == "valid" and bool(action_record_id)


class FixedCostProvider:
    def __init__(self, spent: float) -> None:
        self.spent = spent

    def current_spend_usd(self) -> float:
        return self.spent


def test_execution_blocked_by_paperclip_budget():
    now = datetime.now(timezone.utc)
    publisher = StubPublisher()
    guard = PaperclipRuntimeGuard(cost_provider=FixedCostProvider(9.9), audit_sink=publisher, daily_budget_usd=10.0)

    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="paper"),
        event_publisher=publisher,
        confirm_gate=StubConfirmGate(),
        config=ExecutionConfig(paperclip_guard=guard),
    )

    signal = TradeSignal(
        signal_id="sig-paperclip",
        symbol="BTCUSDT",
        side="buy",
        quantity=0.1,
        confidence=0.9,
        timestamp=now,
        gate_passed=True,
    )
    risk = RiskSnapshot(heartbeat_ts=now, drawdown_pct=1.0, heat_pct=10.0, halt_active=False)

    with pytest.raises(GateCheckError):
        agent.execute(
            signal=signal,
            risk=risk,
            confirm_token="valid",
            action_record_id="a-paperclip",
            stop_loss=59000,
            take_profit=62000,
            estimated_llm_cost_usd=0.2,
            now=now,
        )

    assert any(channel == "governance:paperclip" for channel, _ in publisher.events)
