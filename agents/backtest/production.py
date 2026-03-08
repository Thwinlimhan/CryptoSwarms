from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agents.backtest.models import StrategyCandidate


@dataclass(frozen=True)
class SweepResult:
    params: dict[str, float]
    sharpe: float
    max_drawdown: float
    total_return: float


@dataclass(frozen=True)
class StressResult:
    slippage: float
    sharpe: float
    passed: bool


@dataclass(frozen=True)
class CandidateDecision:
    accepted: bool
    reasons: list[str]


def parameter_sweep(
    candidate: StrategyCandidate,
    param_space: dict[str, list[float]],
    evaluate_fn: Callable[[dict[str, float]], tuple[float, float, float]],
    max_combinations: int = 100,
) -> list[SweepResult]:
    keys = list(param_space.keys())
    if not keys:
        sharpe, drawdown, ret = evaluate_fn(candidate.params)
        return [SweepResult(params=dict(candidate.params), sharpe=sharpe, max_drawdown=drawdown, total_return=ret)]

    results: list[SweepResult] = []

    def _walk(idx: int, current: dict[str, float]) -> None:
        if len(results) >= max_combinations:
            return
        if idx >= len(keys):
            sharpe, drawdown, total_return = evaluate_fn(current)
            results.append(
                SweepResult(
                    params=dict(current),
                    sharpe=float(sharpe),
                    max_drawdown=float(drawdown),
                    total_return=float(total_return),
                )
            )
            return

        key = keys[idx]
        for value in param_space[key]:
            current[key] = float(value)
            _walk(idx + 1, current)
            if len(results) >= max_combinations:
                return

    _walk(0, dict(candidate.params))
    return results


def slippage_stress_test(base_sharpe: float, slippages: list[float], min_sharpe: float = 0.7) -> list[StressResult]:
    out: list[StressResult] = []
    for s in slippages:
        penalized_sharpe = base_sharpe - (s * 3.0)
        out.append(StressResult(slippage=float(s), sharpe=round(penalized_sharpe, 4), passed=penalized_sharpe >= min_sharpe))
    return out


def decide_candidate(
    *,
    best_sharpe: float,
    worst_drawdown: float,
    stress_results: list[StressResult],
    min_sharpe: float = 1.0,
    max_drawdown: float = 0.25,
) -> CandidateDecision:
    reasons: list[str] = []
    if best_sharpe < min_sharpe:
        reasons.append(f"sharpe {best_sharpe:.3f} below threshold {min_sharpe:.3f}")
    if worst_drawdown > max_drawdown:
        reasons.append(f"drawdown {worst_drawdown:.3f} above threshold {max_drawdown:.3f}")
    if any(not result.passed for result in stress_results):
        reasons.append("failed conservative slippage stress")

    return CandidateDecision(accepted=len(reasons) == 0, reasons=reasons)


def export_candidate_report(
    *,
    out_path: Path,
    strategy_id: str,
    sweep_results: list[SweepResult],
    stress_results: list[StressResult],
    decision: CandidateDecision,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "strategy_id": strategy_id,
        "top_results": [
            {
                "params": r.params,
                "sharpe": r.sharpe,
                "max_drawdown": r.max_drawdown,
                "total_return": r.total_return,
            }
            for r in sorted(sweep_results, key=lambda x: x.sharpe, reverse=True)[:10]
        ],
        "stress_results": [{"slippage": r.slippage, "sharpe": r.sharpe, "passed": r.passed} for r in stress_results],
        "decision": {"accepted": decision.accepted, "reasons": decision.reasons},
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
