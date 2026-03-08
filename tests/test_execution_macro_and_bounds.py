from datetime import datetime, timedelta, timezone

import pytest

from agents.execution.execution_agent import (
    BinanceExchangeAdapter,
    ExchangeExecutionError,
    ExecutionAgent,
    ExecutionConfig,
    GateCheckError,
    OrderRequest,
    RiskSnapshot,
    TradeSignal,
)
from cryptoswarms.macro_calendar import MacroEvent


class StubPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


class StubConfirmGate:
    def verify(self, token: str, action_record_id: str) -> bool:
        return token == "valid" and bool(action_record_id)


def _signal(now: datetime, side: str = "buy") -> TradeSignal:
    return TradeSignal(
        signal_id="sig-1",
        symbol="BTCUSDT",
        side=side,
        quantity=0.1,
        confidence=0.9,
        timestamp=now,
        gate_passed=True,
    )


def _risk(now: datetime) -> RiskSnapshot:
    return RiskSnapshot(
        heartbeat_ts=now,
        drawdown_pct=1.0,
        heat_pct=10.0,
        halt_active=False,
    )


def test_macro_blackout_blocks_execution():
    now = datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc)
    event = MacroEvent(name="CPI", at=now + timedelta(minutes=10))

    agent = ExecutionAgent(
        exchange_adapter=BinanceExchangeAdapter(mode="paper"),
        event_publisher=StubPublisher(),
        confirm_gate=StubConfirmGate(),
        config=ExecutionConfig(macro_events_utc=(event,), macro_blackout_minutes=30),
    )

    with pytest.raises(GateCheckError):
        agent.execute(
            signal=_signal(now),
            risk=_risk(now),
            confirm_token="valid",
            action_record_id="a1",
            stop_loss=59000,
            take_profit=63000,
            now=now,
        )


def test_live_adapter_enforces_directional_stoploss_bounds_long():
    adapter = BinanceExchangeAdapter(mode="live")

    with pytest.raises(ExchangeExecutionError):
        adapter.place_order(
            order=OrderRequest(
                symbol="BTCUSDT",
                side="buy",
                quantity=0.1,
                entry_price=60000,
                stop_loss=61000,
                take_profit=62000,
            )
        )


def test_live_adapter_accepts_valid_short_bounds():
    adapter = BinanceExchangeAdapter(mode="live")

    result = adapter.place_order(
        order=OrderRequest(
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            entry_price=60000,
            stop_loss=62000,
            take_profit=58000,
        )
    )

    assert result["status"] == "accepted"
