from datetime import datetime, timedelta, timezone

from cryptoswarms.dag_summarizer import DagSummarizationConfig, maybe_summarize_topic
from cryptoswarms.memory_dag import MemoryDag


def test_maybe_summarize_topic_creates_auto_summary_when_threshold_exceeded():
    dag = MemoryDag()
    now = datetime.now(timezone.utc)
    topic = "default::s1"
    for i in range(45):
        dag.add_node(node_type="research_hypothesis", topic=topic, content=f"content {i} " * 20, created_at=now - timedelta(minutes=i))

    node_id = maybe_summarize_topic(dag, topic=topic, config=DagSummarizationConfig(max_nodes_per_topic=40, trigger_token_budget=1500, summary_max_chars=300))
    assert node_id is not None
    node = dag.get_node(node_id)
    assert node is not None
    assert node.node_type == "auto_summary"


def test_maybe_summarize_topic_noop_when_below_thresholds():
    dag = MemoryDag()
    topic = "default::s2"
    dag.add_node(node_type="research_hypothesis", topic=topic, content="small", created_at=datetime.now(timezone.utc))
    node_id = maybe_summarize_topic(dag, topic=topic, config=DagSummarizationConfig(max_nodes_per_topic=40, trigger_token_budget=1500, summary_max_chars=300))
    assert node_id is None
