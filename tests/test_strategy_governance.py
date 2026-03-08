from cryptoswarms.strategy_governance import (
    StrategyCountPolicy,
    StrategyDurabilityReport,
    enforce_strategy_count,
    is_durable_across_regimes,
)


def test_strategy_count_blocks_multiple_without_durability():
    decision = enforce_strategy_count(["s1", "s2"], durability_report=None)

    assert decision.approved is False
    assert any("durability report" in reason for reason in decision.reasons)


def test_strategy_count_allows_multiple_when_durable():
    report = StrategyDurabilityReport(
        regimes_tested=4,
        profitable_regimes=3,
        min_regime_sharpe=1.1,
        max_regime_drawdown=0.15,
        live_days=90,
    )
    durable, reasons = is_durable_across_regimes(report, policy=StrategyCountPolicy())
    assert durable is True
    assert reasons == []

    decision = enforce_strategy_count(["s1", "s2"], durability_report=report)
    assert decision.approved is True
