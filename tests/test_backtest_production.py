from pathlib import Path

import pytest

from agents.backtest.models import StrategyCandidate
from agents.backtest.production import decide_candidate, export_candidate_report, parameter_sweep, slippage_stress_test


def test_parameter_sweep_respects_limit():
    candidate = StrategyCandidate(
        strategy_id="s1",
        module_path="m",
        class_name="C",
        params={"fast": 10.0},
        market_data=[],
        benchmark_returns=[],
    )

    results = parameter_sweep(
        candidate,
        param_space={"fast": [5, 10, 15], "slow": [20, 30, 40]},
        evaluate_fn=lambda p: (1.2, 0.1, 0.2),
        max_combinations=4,
    )

    assert len(results) == 4


def test_decide_candidate_rejects_on_stress_failure():
    stress = slippage_stress_test(base_sharpe=1.0, slippages=[0.001, 0.004], min_sharpe=0.99)
    decision = decide_candidate(best_sharpe=1.0, worst_drawdown=0.2, stress_results=stress, min_sharpe=0.9, max_drawdown=0.3)
    assert decision.accepted is False
    assert any("slippage" in reason for reason in decision.reasons)


def test_export_candidate_report_writes_file(tmp_path: Path):
    out = export_candidate_report(
        out_path=tmp_path / "report.json",
        strategy_id="s1",
        sweep_results=[],
        stress_results=[],
        decision=decide_candidate(best_sharpe=1.2, worst_drawdown=0.1, stress_results=[]),
    )
    assert out.exists()


def test_export_candidate_report_blocks_non_idempotent_overwrite(tmp_path: Path):
    path = tmp_path / "report.json"
    export_candidate_report(
        out_path=path,
        strategy_id="s1",
        sweep_results=[],
        stress_results=[],
        decision=decide_candidate(best_sharpe=1.2, worst_drawdown=0.1, stress_results=[]),
    )
    with pytest.raises(FileExistsError):
        export_candidate_report(
            out_path=path,
            strategy_id="s2",
            sweep_results=[],
            stress_results=[],
            decision=decide_candidate(best_sharpe=1.2, worst_drawdown=0.1, stress_results=[]),
        )
