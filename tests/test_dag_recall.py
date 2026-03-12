from datetime import datetime, timedelta, timezone

from cryptoswarms.dag_recall import DagWalker
from cryptoswarms.memory_dag import MemoryDag


def test_dag_walker_recall_respects_topic_and_budget():
    dag = MemoryDag()
    now = datetime.now(timezone.utc)
    dag.add_node(node_type="summary", topic="s1", content="alpha " * 120, created_at=now - timedelta(hours=1))
    dag.add_node(node_type="summary", topic="s1", content="beta " * 120, created_at=now - timedelta(hours=2))
    dag.add_node(node_type="summary", topic="s2", content="gamma " * 120, created_at=now - timedelta(hours=1))

    walker = DagWalker(dag)
    out = walker.recall(topic="s1", lookback_hours=24, max_nodes=10, token_budget=200)

    assert out.nodes
    assert all(n.topic == "s1" for n in out.nodes)
    assert out.token_estimate <= 200


def test_dag_walker_applies_provenance_decay_filter():
    dag = MemoryDag()
    now = datetime.now(timezone.utc)

    fresh = dag.add_node(
        node_type="research_hypothesis",
        topic="s1",
        content="fresh context",
        metadata={"confidence": 0.8},
        created_at=now - timedelta(hours=2),
    )
    dag.add_node(
        node_type="research_hypothesis",
        topic="s1",
        content="stale weak context",
        metadata={"confidence": 0.3},
        created_at=now - timedelta(days=7),
    )

    walker = DagWalker(dag)
    out = walker.recall(
        topic="s1",
        lookback_hours=24 * 14,
        max_nodes=10,
        token_budget=2000,
        provenance_half_life_hours=24,
        min_provenance_confidence=0.2,
    )

    ids = {n.node_id for n in out.nodes}
    assert fresh.node_id in ids
    assert all(float(n.metadata.get("provenance_confidence", 0.0)) >= 0.2 for n in out.nodes)
