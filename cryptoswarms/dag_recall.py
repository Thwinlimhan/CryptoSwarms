from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptoswarms.memory_dag import MemoryDag, MemoryDagNode


@dataclass(frozen=True)
class DagRecallResult:
    nodes: list[MemoryDagNode]
    token_estimate: int
    truncated: bool


class DagWalker:
    def __init__(self, dag: MemoryDag) -> None:
        self.dag = dag

    def recall(
        self,
        *,
        topic: str,
        lookback_hours: int = 72,
        max_nodes: int = 8,
        token_budget: int = 800,
        provenance_half_life_hours: int = 72,
        min_provenance_confidence: float = 0.15,
        now: datetime | None = None,
    ) -> DagRecallResult:
        now_dt = now or datetime.now(timezone.utc)
        cutoff = now_dt - timedelta(hours=max(1, int(lookback_hours)))

        candidates = [n for n in self.dag.latest_by_topic(topic, limit=200) if n.created_at >= cutoff]
        selected: list[MemoryDagNode] = []
        used = 0
        truncated = False

        for node in candidates[: max(1, int(max_nodes))]:
            provenance_confidence = _provenance_confidence(
                node=node,
                now=now_dt,
                half_life_hours=provenance_half_life_hours,
            )
            if provenance_confidence < min_provenance_confidence:
                continue

            node.metadata["provenance_confidence"] = round(provenance_confidence, 4)
            node.metadata["age_hours"] = round((now_dt - node.created_at).total_seconds() / 3600.0, 3)

            estimate = max(1, len(node.content) // 4)
            if used + estimate > max(100, int(token_budget)):
                truncated = True
                break
            selected.append(node)
            used += estimate

        return DagRecallResult(nodes=selected, token_estimate=used, truncated=truncated)


def _provenance_confidence(*, node: MemoryDagNode, now: datetime, half_life_hours: int) -> float:
    age_hours = max(0.0, (now - node.created_at).total_seconds() / 3600.0)

    metadata = node.metadata or {}
    base = metadata.get("confidence", metadata.get("posterior_probability", 1.0))
    try:
        base_conf = float(base)
    except (TypeError, ValueError):
        base_conf = 1.0
    base_conf = max(0.0, min(1.0, base_conf))

    hl = max(1.0, float(half_life_hours))
    decay = 0.5 ** (age_hours / hl)
    return max(0.0, min(1.0, base_conf * decay))
