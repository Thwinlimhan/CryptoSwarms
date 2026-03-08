from cryptoswarms.risk import CircuitBreakerLevel, RiskSnapshot, evaluate_circuit_breaker


def test_normal_operations():
    result = evaluate_circuit_breaker(RiskSnapshot(daily_drawdown_pct=1.2, portfolio_heat_pct=9.0))
    assert result.level == CircuitBreakerLevel.NORMAL
    assert result.allow_new_entries is True


def test_warning_level_1():
    result = evaluate_circuit_breaker(RiskSnapshot(daily_drawdown_pct=3.2, portfolio_heat_pct=10.0))
    assert result.level == CircuitBreakerLevel.L1_WARNING
    assert result.reduce_position_size_pct == 50


def test_caution_level_2_by_heat():
    result = evaluate_circuit_breaker(RiskSnapshot(daily_drawdown_pct=2.0, portfolio_heat_pct=18.0))
    assert result.level == CircuitBreakerLevel.L2_CAUTION
    assert result.allow_new_entries is False


def test_halt_level_3_by_drawdown():
    result = evaluate_circuit_breaker(RiskSnapshot(daily_drawdown_pct=5.4, portfolio_heat_pct=14.0))
    assert result.level == CircuitBreakerLevel.L3_HALT
    assert result.require_manual_resume is True


def test_emergency_level_4_by_liquidation_proximity():
    result = evaluate_circuit_breaker(
        RiskSnapshot(daily_drawdown_pct=1.0, portfolio_heat_pct=8.0, near_liquidation=True)
    )
    assert result.level == CircuitBreakerLevel.L4_EMERGENCY
