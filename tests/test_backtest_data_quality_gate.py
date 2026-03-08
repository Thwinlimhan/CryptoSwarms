from agents.backtest.gates import ValidationThresholds, gate_0_data_quality
from agents.backtest.models import GateStatus, StrategyCandidate


def _candidate(close_series: list[float | None]) -> StrategyCandidate:
    return StrategyCandidate(
        strategy_id="s1",
        module_path="fake.py",
        class_name="FakeStrategy",
        params={"length": 20.0},
        market_data={"close": close_series},
        benchmark_returns=[],
    )


def test_data_quality_gate_passes_for_clean_series():
    candidate = _candidate([100.0, 101.0, 102.5, 103.0, 104.2])
    result = gate_0_data_quality(candidate, ValidationThresholds())

    assert result.status == GateStatus.PASS
    assert result.gate_number == 0


def test_data_quality_gate_fails_for_missing_values():
    candidate = _candidate([100.0, None, 101.0, None, 102.0, None])
    thresholds = ValidationThresholds(max_missing_ratio=0.2)
    result = gate_0_data_quality(candidate, thresholds)

    assert result.status == GateStatus.FAIL
    assert result.details["missing_ratio"] > thresholds.max_missing_ratio


def test_data_quality_gate_fails_for_large_outlier_return():
    candidate = _candidate([100.0, 102.0, 300.0])
    thresholds = ValidationThresholds(max_abs_outlier_return=0.5)
    result = gate_0_data_quality(candidate, thresholds)

    assert result.status == GateStatus.FAIL
    assert result.details["max_abs_return"] > thresholds.max_abs_outlier_return
