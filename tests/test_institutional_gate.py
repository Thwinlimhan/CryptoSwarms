from agents.backtest.institutional_gate import (
    InstitutionalBenchmark,
    InstitutionalGatePolicy,
    evaluate_institutional_benchmark,
)


def test_institutional_benchmark_accepts_strong_metrics():
    benchmark = InstitutionalBenchmark(
        strategy_sharpe=1.35,
        strategy_max_drawdown=0.14,
        strategy_profit_factor=1.45,
        strategy_trade_count=160,
        baseline_sharpe=1.1,
        baseline_max_drawdown=0.18,
    )

    decision = evaluate_institutional_benchmark(benchmark, policy=InstitutionalGatePolicy())

    assert decision.accepted is True
    assert decision.reasons == []


def test_institutional_benchmark_rejects_when_drawdown_and_trade_count_fail():
    benchmark = InstitutionalBenchmark(
        strategy_sharpe=1.0,
        strategy_max_drawdown=0.27,
        strategy_profit_factor=1.1,
        strategy_trade_count=80,
        baseline_sharpe=1.0,
        baseline_max_drawdown=0.2,
    )

    decision = evaluate_institutional_benchmark(benchmark, policy=InstitutionalGatePolicy())

    assert decision.accepted is False
    assert any("drawdown" in reason for reason in decision.reasons)
    assert any("trade count" in reason for reason in decision.reasons)
