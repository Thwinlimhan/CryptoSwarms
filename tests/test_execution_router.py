from datetime import datetime, timedelta, timezone

from cryptoswarms.deadman import DeadMansSwitchState
from cryptoswarms.execution_router import ExecutionRouter, OrderIntent
from cryptoswarms.risk import RiskSnapshot


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[OrderIntent, bool]] = []

    def execute(self, intent: OrderIntent, reduce_only: bool = False) -> None:
        self.calls.append((intent, reduce_only))


def test_router_accepts_when_gate_allows_entries():
    now = datetime.now(timezone.utc)
    executor = FakeExecutor()
    router = ExecutionRouter(executor)

    decision = router.route(
        intent=OrderIntent(symbol="BTCUSDT", side="BUY", quantity=0.1),
        now=now,
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=1.0, portfolio_heat_pct=5.0),
        last_risk_heartbeat=now - timedelta(seconds=5),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )

    assert decision.accepted is True
    assert len(executor.calls) == 1
    assert executor.calls[0][1] is False


def test_router_blocks_new_entry_in_reductions_only_mode():
    now = datetime.now(timezone.utc)
    executor = FakeExecutor()
    router = ExecutionRouter(executor)

    decision = router.route(
        intent=OrderIntent(symbol="BTCUSDT", side="BUY", quantity=0.1, reduce_only=False),
        now=now,
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=4.5, portfolio_heat_pct=5.0),
        last_risk_heartbeat=now - timedelta(seconds=5),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )

    assert decision.accepted is False
    assert decision.effective_reduce_only is True
    assert len(executor.calls) == 0


def test_router_allows_reduce_only_order_when_gated():
    now = datetime.now(timezone.utc)
    executor = FakeExecutor()
    router = ExecutionRouter(executor)

    decision = router.route(
        intent=OrderIntent(symbol="BTCUSDT", side="SELL", quantity=0.1, reduce_only=True),
        now=now,
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=4.5, portfolio_heat_pct=5.0),
        last_risk_heartbeat=now - timedelta(seconds=5),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )

    assert decision.accepted is True
    assert decision.effective_reduce_only is True
    assert len(executor.calls) == 1
    assert executor.calls[0][1] is True
