from datetime import datetime, timezone

from agents.research.deerflow_pipeline import ResearchItem
from agents.research.research_factory import KnowledgeBase, KnowledgeDocument, ResearchFactory
from cryptoswarms.failure_ledger import FailureLedger
from cryptoswarms.memory_dag import MemoryDag


class StaticConnector:
    def fetch_latest(self):
        now = datetime(2026, 3, 8, tzinfo=timezone.utc)
        return [
            ResearchItem(
                source="news",
                title="Bitcoin breakout with inflow",
                content="Momentum breakout with ETF inflow and rising participation.",
                url="https://example.com/news1",
                published_at=now,
            )
        ]


class InMemoryQueue:
    def __init__(self):
        self.items = []

    def publish(self, payload: dict[str, object]) -> None:
        self.items.append(payload)


def test_research_factory_emits_hypotheses_and_backtest_requests():
    kb = KnowledgeBase(
        documents=[
            KnowledgeDocument(
                doc_id="doc-1",
                title="Momentum and Regimes",
                source="paper",
                content="Use regime-aware filters for momentum in crypto assets.",
                tags=("momentum", "regime"),
            )
        ]
    )
    queue = InMemoryQueue()
    ledger = FailureLedger()
    ledger.record(key="phase1-btc-breakout-15m", passed=True)
    factory = ResearchFactory(connectors=[StaticConnector()], knowledge_base=kb, queue=queue, failure_ledger=ledger)

    report = factory.run(symbol="BTCUSDT", max_hypotheses=3, now=datetime(2026, 3, 8, tzinfo=timezone.utc))

    assert report.hypotheses_emitted == 1
    assert len(report.backtest_requests) == 1
    assert queue.items[0]["event"] == "research_hypothesis"
    assert queue.items[0]["strategy_id"] == "phase1-btc-breakout-15m"
    assert "decision_math" in queue.items[0]
    assert "kelly_fraction" in report.backtest_requests[0].params


def test_knowledge_base_search_scores_by_overlap():
    kb = KnowledgeBase(
        documents=[
            KnowledgeDocument("d1", "Momentum Alpha", "book", "momentum breakout inflow", ("momentum",)),
            KnowledgeDocument("d2", "Mean Reversion", "book", "range and mean reversion", ("reversion",)),
        ]
    )

    docs = kb.search("breakout momentum", limit=1)

    assert len(docs) == 1
    assert docs[0].doc_id == "d1"


def test_research_factory_uses_memory_context_and_writes_memory_checkpoint():
    kb = KnowledgeBase(
        documents=[
            KnowledgeDocument(
                doc_id="doc-1",
                title="Momentum and Regimes",
                source="paper",
                content="Use regime-aware filters for momentum in crypto assets.",
                tags=("momentum", "regime"),
            )
        ]
    )
    queue = InMemoryQueue()
    dag = MemoryDag()
    prior = dag.add_node(
        node_type="decision_checkpoint",
        topic="phase1-btc-breakout-15m",
        content="prior decision context",
        created_at=datetime(2026, 3, 7, tzinfo=timezone.utc),
    )

    factory = ResearchFactory(connectors=[StaticConnector()], knowledge_base=kb, queue=queue, memory_dag=dag)
    factory.run(symbol="BTCUSDT", max_hypotheses=1, now=datetime(2026, 3, 8, tzinfo=timezone.utc))

    assert len(queue.items) == 1
    memory_payload = queue.items[0]["memory"]
    assert prior.node_id in memory_payload["context_node_ids"]
    assert memory_payload["checkpoint_node_id"] is not None
    checkpoint = dag.get_node(memory_payload["checkpoint_node_id"])
    assert checkpoint is not None
    assert checkpoint.node_type == "research_hypothesis"
    assert checkpoint.topic == "phase1-btc-breakout-15m"

