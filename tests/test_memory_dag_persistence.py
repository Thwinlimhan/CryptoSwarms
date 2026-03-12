from datetime import datetime, timezone

from cryptoswarms.memory_dag import MemoryDag


def test_memory_dag_json_roundtrip(tmp_path):
    path = tmp_path / "memory_dag.json"
    dag = MemoryDag()
    a = dag.add_node(
        node_type="raw_event",
        topic="phase1-btc-breakout-15m",
        content="event-a",
        metadata={"source": "test"},
        created_at=datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc),
    )
    b = dag.add_node(
        node_type="summary",
        topic="phase1-btc-breakout-15m",
        content="summary-b",
        created_at=datetime(2026, 3, 8, 11, 0, tzinfo=timezone.utc),
    )
    dag.add_edge(from_node_id=a.node_id, to_node_id=b.node_id)
    dag.save_json(path)

    loaded = MemoryDag.load_json(path)
    assert len(loaded.nodes()) == 2
    assert len(loaded.edges()) == 1
    latest = loaded.latest_by_topic("phase1-btc-breakout-15m", limit=1)
    assert latest[0].node_id == b.node_id


def test_memory_dag_load_json_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "missing.json"
    loaded = MemoryDag.load_json(missing)
    assert loaded.nodes() == []
    assert loaded.edges() == []

