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
    gate_7_swarm_regime,
    gate_8_recipe_alignment,
    gate_9_hyperspace_consensus,
    gate_10_funding_arbitrage,
)
from .mirofish_simulator import MiroFishRegimeSimulator
import asyncio
from agents.orchestration.subagent_executor import SubagentExecutor, SubagentTask
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
    mirofish_simulator: MiroFishRegimeSimulator | None = None
    lob_connector: Any | None = None  # HyperliquidLOBConnector
    mesh_client: Any | None = None    # HyperspaceMeshClient
    funding_connector: Any | None = None  # HyperliquidFundingConnector

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

        if self.mirofish_simulator is not None:
            gate_7 = gate_7_swarm_regime(candidate, self.mirofish_simulator)
            gate_results.append(gate_7)
            persist_gate_result(self.db, run_id, candidate.strategy_id, gate_7)

        if self.lob_connector is not None:
            gate_8 = gate_8_recipe_alignment(candidate, self.lob_connector)
            gate_results.append(gate_8)
            persist_gate_result(self.db, run_id, candidate.strategy_id, gate_8)

        if self.mesh_client is not None:
            gate_9 = gate_9_hyperspace_consensus(candidate, self.mesh_client)
            gate_results.append(gate_9)
            persist_gate_result(self.db, run_id, candidate.strategy_id, gate_9)

        if self.funding_connector is not None and candidate.params.get("strategy_type") == "funding_arbitrage":
            gate_10 = gate_10_funding_arbitrage(candidate, self.funding_connector)
            gate_results.append(gate_10)
            persist_gate_result(self.db, run_id, candidate.strategy_id, gate_10)

        return self._finalize(candidate.strategy_id, run_id, gate_results)

    async def run_parallel_gates(self, candidate: StrategyCandidate) -> ValidationSummary:
        """
        Parallel gate execution using your existing SubagentExecutor.
        Gates 2-6 are independent given a syntax-passing candidate — run them in parallel.
        Gates 0, 1 must run sequentially first (they are prerequisites).
        """
        run_id = str(uuid4())
        ensure_validations_table(self.db)

        # ── Sequential prerequisite gates (must run first) ─────────────────────
        gate_1 = gate_1_syntax_check(candidate)
        if gate_1.status != GateStatus.PASS:
            return self._finalize(candidate.strategy_id, run_id, [gate_1])

        gate_0 = gate_0_data_quality(candidate, self.thresholds)
        if gate_0.status != GateStatus.PASS:
            return self._finalize(candidate.strategy_id, run_id, [gate_1, gate_0])

        # ── Parallel independent gates (2-6 can all run simultaneously) ────────
        executor = SubagentExecutor(max_parallelism=5, timeout_seconds=30.0)

        async def run_gate(task: SubagentTask) -> dict:
            name = task.role
            if name == "sensitivity":
                r = gate_2_sensitivity(candidate, self.backtest_runner, self.thresholds)
            elif name == "vectorbt":
                r = gate_3_vectorbt_screen(candidate, self.vectorbt_runner, self.thresholds)
            elif name == "walk_forward":
                r = gate_4_walk_forward(candidate, self.jesse_adapter.walk_forward, self.thresholds)
            elif name == "regime":
                r = gate_5_regime_evaluation(candidate, self.backtest_runner, self.thresholds, self.regime_tagger)
            elif name == "correlation":
                r = gate_6_correlation_check(candidate, self.backtest_runner, self.active_returns_provider, self.thresholds)
            else:
                return {"error": f"unknown gate: {name}"}
            persist_gate_result(self.db, run_id, candidate.strategy_id, r)
            return {"gate_result": r}

        parallel_tasks = [
            SubagentTask(task_id=f"{run_id}-{name}", role=name, payload={})
            for name in ["sensitivity", "vectorbt", "walk_forward", "regime", "correlation"]
        ]
        report = await executor.run(parallel_tasks, run_gate)

        # Collect gate results in order
        gate_results = [gate_1, gate_0]
        gate_order = ["sensitivity", "vectorbt", "walk_forward", "regime", "correlation"]
        result_map = {r.role: r.output.get("gate_result") for r in report.results if r.status == "ok"}
        for name in gate_order:
            if gr := result_map.get(name):
                gate_results.append(gr)

        return self._finalize(candidate.strategy_id, run_id, gate_results)

    def _finalize(self, strategy_id: str, run_id: str, gate_results: list[GateResult]) -> ValidationSummary:
        summary = ValidationSummary(strategy_id=strategy_id, run_id=run_id, gate_results=gate_results)
        emit_validation_event(self.execution_queue, summary)
        return summary
