from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .adapters import DefaultRegimeTagger, JesseAdapter, TimescaleActiveReturnsProvider
from .gates import (
    ValidationThresholds,
    gate_0_data_quality,
    gate_1_syntax_check,
    gate_2_sensitivity,
    gate_3_vectorbt_screen,
    gate_4_walk_forward,
    gate_5_regime_evaluation,
    gate_6_correlation_check,
)
from .models import GateResult, GateStatus, StrategyCandidate, ValidationSummary
from .persistence import DBConnection, ensure_validations_table, persist_gate_result
from .queueing import ExecutionQueue, emit_validation_event


@dataclass(slots=True)
class ValidationPipeline:
    db: DBConnection
    execution_queue: ExecutionQueue
    backtest_runner: Any
    vectorbt_runner: Any
    jesse_adapter: JesseAdapter
    active_returns_provider: TimescaleActiveReturnsProvider
    regime_tagger: Any = field(default_factory=DefaultRegimeTagger)
    thresholds: ValidationThresholds = field(default_factory=ValidationThresholds)

    def run(self, candidate: StrategyCandidate, run_id: str | None = None) -> ValidationSummary:
        run_id = run_id or str(uuid4())
        ensure_validations_table(self.db)

        gate_results: list[GateResult] = []

        gate_1 = gate_1_syntax_check(candidate)
        gate_results.append(gate_1)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_1)
        if gate_1.status != GateStatus.PASS:
            return self._finalize(candidate.strategy_id, run_id, gate_results)

        gate_0 = gate_0_data_quality(candidate, self.thresholds)
        gate_results.append(gate_0)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_0)
        if gate_0.status != GateStatus.PASS:
            return self._finalize(candidate.strategy_id, run_id, gate_results)

        gate_2 = gate_2_sensitivity(candidate, self.backtest_runner, self.thresholds)
        gate_results.append(gate_2)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_2)

        gate_3 = gate_3_vectorbt_screen(candidate, self.vectorbt_runner, self.thresholds)
        gate_results.append(gate_3)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_3)

        gate_4 = gate_4_walk_forward(candidate, self.jesse_adapter.walk_forward, self.thresholds)
        gate_results.append(gate_4)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_4)

        gate_5 = gate_5_regime_evaluation(candidate, self.backtest_runner, self.thresholds, self.regime_tagger)
        gate_results.append(gate_5)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_5)

        gate_6 = gate_6_correlation_check(candidate, self.backtest_runner, self.active_returns_provider, self.thresholds)
        gate_results.append(gate_6)
        persist_gate_result(self.db, run_id, candidate.strategy_id, gate_6)

        return self._finalize(candidate.strategy_id, run_id, gate_results)

    def _finalize(self, strategy_id: str, run_id: str, gate_results: list[GateResult]) -> ValidationSummary:
        summary = ValidationSummary(strategy_id=strategy_id, run_id=run_id, gate_results=gate_results)
        emit_validation_event(self.execution_queue, summary)
        return summary
