from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from cryptoswarms.dag_recall import DagRecallResult, DagWalker
from cryptoswarms.memory_dag import MemoryDag


class CouncilInputLike(Protocol):
    strategy_id: str
    project_id: str


class CouncilDecisionLike(Protocol):
    decision: str
    confidence: float
    dissent_ratio: float
    reason: str
    passed_governor: bool
    stages: list[str]
    aggregate: object


@dataclass(frozen=True)
class DagBridgeConfig:
    recall_lookback_hours: int = 72
    recall_max_nodes: int = 8
    recall_token_budget: int = 800


class DagMemoryBridge:
    def __init__(self, dag: MemoryDag, config: DagBridgeConfig = DagBridgeConfig()) -> None:
        self.dag = dag
        self.config = config

    @staticmethod
    def scoped_topic(*, project_id: str, strategy_id: str) -> str:
        return f"{project_id}::{strategy_id}"

    def recall_for_decision(self, payload: CouncilInputLike) -> DagRecallResult:
        walker = DagWalker(self.dag)
        scoped = walker.recall(
            topic=self.scoped_topic(project_id=payload.project_id, strategy_id=payload.strategy_id),
            lookback_hours=self.config.recall_lookback_hours,
            max_nodes=self.config.recall_max_nodes,
            token_budget=self.config.recall_token_budget,
        )
        legacy = walker.recall(
            topic=payload.strategy_id,
            lookback_hours=self.config.recall_lookback_hours,
            max_nodes=self.config.recall_max_nodes,
            token_budget=self.config.recall_token_budget,
        )

        merged: list = []
        seen: set[str] = set()
        for node in list(scoped.nodes) + list(legacy.nodes):
            if node.node_id in seen:
                continue
            seen.add(node.node_id)
            merged.append(node)
        merged.sort(key=lambda n: n.created_at, reverse=True)
        trimmed = merged[: self.config.recall_max_nodes]

        token_estimate = sum(max(1, len(n.content) // 4) for n in trimmed)
        return DagRecallResult(
            nodes=trimmed,
            token_estimate=token_estimate,
            truncated=len(merged) > len(trimmed),
        )

    def write_decision_checkpoint(self, *, payload: CouncilInputLike, decision: CouncilDecisionLike) -> str:
        now = datetime.now(timezone.utc)
        aggregate = getattr(decision, "aggregate", None)
        summary = (
            f"decision={decision.decision} conf={decision.confidence:.3f} dissent={decision.dissent_ratio:.3f} "
            f"reason={decision.reason}"
        )
        node = self.dag.add_node(
            node_type="decision_checkpoint",
            topic=self.scoped_topic(project_id=payload.project_id, strategy_id=payload.strategy_id),
            content=summary,
            created_at=now,
            metadata={
                "project_id": payload.project_id,
                "strategy_id": payload.strategy_id,
                "passed_governor": decision.passed_governor,
                "stages": list(decision.stages),
                "aggregate": {
                    "decision": getattr(aggregate, "decision", "hold"),
                    "confidence": getattr(aggregate, "confidence", 0.0),
                    "dissent_ratio": getattr(aggregate, "dissent_ratio", 0.0),
                    "vote_count": getattr(aggregate, "vote_count", 0),
                },
            },
        )

        prior_nodes = self.dag.latest_by_topic(
            self.scoped_topic(project_id=payload.project_id, strategy_id=payload.strategy_id),
            limit=2,
        )
        for prior in prior_nodes:
            if prior.node_id != node.node_id:
                try:
                    self.dag.add_edge(from_node_id=prior.node_id, to_node_id=node.node_id)
                except Exception:
                    pass

        return node.node_id

