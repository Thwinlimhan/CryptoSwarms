from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from cryptoswarms.memory_dag import MemoryDag, MemoryDagNode


@dataclass(frozen=True)
class DagSummarizationConfig:
    max_nodes_per_topic: int = 40
    trigger_token_budget: int = 1800
    summary_max_chars: int = 700


@dataclass(frozen=True)
class DagSummarizationResult:
    summarized_topics: int
    summary_node_ids: list[str]


def maybe_summarize_topic(dag: MemoryDag, *, topic: str, config: DagSummarizationConfig) -> str | None:
    nodes = dag.latest_by_topic(topic, limit=300)
    if len(nodes) <= config.max_nodes_per_topic:
        token_estimate = sum(max(1, len(n.content) // 4) for n in nodes)
        if token_estimate <= config.trigger_token_budget:
            return None

    parts: list[str] = []
    for node in nodes[: min(len(nodes), 16)]:
        snippet = node.content.strip().replace("\n", " ")
        if snippet:
            parts.append(f"[{node.node_type}] {snippet[:120]}")
    summary_text = " | ".join(parts)[: config.summary_max_chars]
    if not summary_text:
        summary_text = "auto-summary"

    summary = dag.add_node(
        node_type="auto_summary",
        topic=topic,
        content=summary_text,
        created_at=datetime.now(timezone.utc),
        metadata={
            "source_node_count": len(nodes),
            "kind": "adaptive_compaction",
        },
    )

    for node in nodes[:8]:
        if node.node_id == summary.node_id:
            continue
        try:
            dag.add_edge(from_node_id=node.node_id, to_node_id=summary.node_id)
        except Exception:
            pass

    return summary.node_id


def maybe_summarize_topics(
    dag: MemoryDag,
    *,
    topics: Iterable[str],
    config: DagSummarizationConfig = DagSummarizationConfig(),
) -> DagSummarizationResult:
    ids: list[str] = []
    for topic in topics:
        out = maybe_summarize_topic(dag, topic=topic, config=config)
        if out:
            ids.append(out)
    return DagSummarizationResult(summarized_topics=len(ids), summary_node_ids=ids)
