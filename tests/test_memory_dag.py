from datetime import datetime, timezone

from cryptoswarms.memory_dag import MemoryDag


def test_memory_dag_adds_nodes_and_edges_without_cycles():
    dag = MemoryDag()
    a = dag.add_node(node_type="raw_event", topic="s1", content="event-a")
    b = dag.add_node(node_type="summary", topic="s1", content="summary-b")

    dag.add_edge(from_node_id=a.node_id, to_node_id=b.node_id)
    assert len(dag.edges()) == 1


def test_memory_dag_rejects_cycle():
    dag = MemoryDag()
    a = dag.add_node(node_type="raw_event", topic="s1", content="event-a")
    b = dag.add_node(node_type="summary", topic="s1", content="summary-b")

    dag.add_edge(from_node_id=a.node_id, to_node_id=b.node_id)
    try:
        dag.add_edge(from_node_id=b.node_id, to_node_id=a.node_id)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_latest_by_topic():
    dag = MemoryDag()
    dag.add_node(node_type="raw_event", topic="x", content="x1", created_at=datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc))
    dag.add_node(node_type="raw_event", topic="x", content="x2", created_at=datetime(2026, 3, 8, 11, 0, tzinfo=timezone.utc))
    out = dag.latest_by_topic("x", limit=1)
    assert len(out) == 1
    assert out[0].content == "x2"
