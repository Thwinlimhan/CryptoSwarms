from agents.research.composite_connector import CompositeNewsConnector
from agents.research.deerflow_pipeline import ResearchItem


class StaticConnector:
    def __init__(self, source: str):
        self.source = source

    def fetch_latest(self):
        return [
            ResearchItem(
                source=self.source,
                title="T",
                content="C",
                url="https://example.com/1",
                published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
        ]


def test_composite_connector_deduplicates_by_source_and_url():
    connector = CompositeNewsConnector([StaticConnector("camoufox"), StaticConnector("camoufox")])
    items = connector.fetch_latest()
    assert len(items) == 1
