from datetime import datetime, timezone

from agents.research.literature_connector import LiteratureConnector, LiteratureDoc, dedupe_literature_docs


def test_dedupe_literature_docs_removes_duplicates():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    docs = [
        LiteratureDoc("A", "x", "https://a", now),
        LiteratureDoc("A", "y", "https://a", now),
        LiteratureDoc("B", "z", "https://b", now),
    ]

    deduped = dedupe_literature_docs(docs)
    assert len(deduped) == 2


def test_literature_connector_emits_research_items():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    connector = LiteratureConnector(
        fetch_fn=lambda: [
            LiteratureDoc("Paper 1", "Abstract", "https://arxiv.org/abs/1", now)
        ]
    )

    items = connector.fetch_latest()
    assert len(items) == 1
    assert items[0].source == "literature"
