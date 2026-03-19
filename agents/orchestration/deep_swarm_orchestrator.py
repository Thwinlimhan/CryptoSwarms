# agents/orchestration/deep_swarm_orchestrator.py

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from agents.backtest.validation_pipeline import ValidationPipeline
from agents.evolution.autoresearch import AutoResearchPolicy
from agents.evolution.deep_agent_evolver import DeepAgentEvolver
from agents.orchestration.hyperspace_mesh import HyperspaceMeshClient
from cryptoswarms.memory_dag import MemoryDag


@dataclass(slots=True)
class DeepSwarmOrchestrator:
    """
    Nightly orchestration cycle: Deep Agent code evolution → Hyperspace gossip.
    All fields are required — wire in production.py.
    """
    policy: AutoResearchPolicy
    validation_pipeline: ValidationPipeline
    score_fn: Callable[[dict], float]
    candidate_builder: Callable
    memory_dag: MemoryDag
    mesh_client: HyperspaceMeshClient | None = None   # optional; gossip only if connected
    incumbent_score: float = 0.0

    async def nightly_cycle(self) -> dict:
        started = datetime.now(timezone.utc)

        # ── 1. Deep Agent evolves code overnight ───────────────────────────
        evolver = DeepAgentEvolver(
            policy=self.policy,
            validation_pipeline=self.validation_pipeline,
            score_fn=self.score_fn,
            candidate_builder=self.candidate_builder,
        )
        report = await evolver.run_async(self.incumbent_score)

        # ── 2. Update incumbent if any experiments were kept ───────────────
        if report.kept:
            self.incumbent_score = report.final_incumbent_score

        # ── 3. Persist to MemoryDag ────────────────────────────────────────
        self.memory_dag.add_node(
            node_type="evolution_report",
            topic="nightly_evolution",
            content=f"score={report.final_incumbent_score:.4f} kept={len(report.kept)} experiments={report.experiments_run}",
            metadata={
                "kept_count": len(report.kept),
                "discarded_count": len(report.discarded),
                "final_score": report.final_incumbent_score,
                "started_at": started.isoformat(),
            },
        )

        # ── 4. Gossip winners to Hyperspace mesh (best-effort) ─────────────
        if self.mesh_client is not None and report.kept:
            for decision in report.kept:
                try:
                    await asyncio.to_thread(
                        self.mesh_client.gossip_validation_result,
                        strategy_id=f"evolved-{started.date()}",
                        gate_results=[],
                        final_score=decision.best_score,
                    )
                except Exception:
                    pass  # gossip is best-effort, never block the cycle

        return {
            "cycle_date": started.date().isoformat(),
            "incumbent_before": report.kept[0].incumbent_before if report.kept else self.incumbent_score,
            "incumbent_after": report.final_incumbent_score,
            "experiments_run": report.experiments_run,
            "kept": len(report.kept),
            "discarded": len(report.discarded),
        }
