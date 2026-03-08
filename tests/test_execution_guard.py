from datetime import datetime, timedelta, timezone

from cryptoswarms.deadman import DeadMansSwitchState
from cryptoswarms.execution_guard import evaluate_pre_execution_gate
from cryptoswarms.risk import CircuitBreakerLevel, RiskSnapshot


def test_deadman_halt_overrides_normal_risk():
    now = datetime.now(timezone.utc)
    decision = evaluate_pre_execution_gate(
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=0.5, portfolio_heat_pct=3.0),
        now=now,
        last_risk_heartbeat=now - timedelta(minutes=10),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )
    assert decision.allow_entries is False
    assert decision.allow_reductions_only is True
    assert "Dead-man switch active" in decision.blocked_reason


def test_risk_gate_blocks_entries_when_deadman_healthy():
    now = datetime.now(timezone.utc)
    decision = evaluate_pre_execution_gate(
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=4.2, portfolio_heat_pct=10.0),
        now=now,
        last_risk_heartbeat=now - timedelta(seconds=10),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )
    assert decision.allow_entries is False
    assert decision.allow_reductions_only is True
    assert decision.risk_decision.level == CircuitBreakerLevel.L2_CAUTION


def test_entries_allowed_when_deadman_healthy_and_risk_normal():
    now = datetime.now(timezone.utc)
    decision = evaluate_pre_execution_gate(
        risk_snapshot=RiskSnapshot(daily_drawdown_pct=1.0, portfolio_heat_pct=8.0),
        now=now,
        last_risk_heartbeat=now - timedelta(seconds=5),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )
    assert decision.allow_entries is True
    assert decision.allow_reductions_only is False
    assert decision.blocked_reason == ""
