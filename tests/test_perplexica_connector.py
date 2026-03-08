from agents.research.perplexica_connector import PerplexicaNewsConnector


def test_perplexica_connector_parses_results():
    def fake_query(base_url: str, query: str, timeout: float):
        return {
            "results": [
                {"title": "BTC momentum", "snippet": "Bullish breakout", "url": "https://example.com/a"},
                {"title": "ETH inflow", "snippet": "Funds rotate", "url": "https://example.com/b"},
            ]
        }

    connector = PerplexicaNewsConnector(
        base_url="http://localhost:3001",
        queries=["bitcoin news"],
        query_fn=fake_query,
    )

    items = connector.fetch_latest()
    assert len(items) == 2
    assert items[0].source == "perplexica"


def test_perplexica_connector_handles_failures():
    def fail_query(base_url: str, query: str, timeout: float):
        raise RuntimeError("offline")

    connector = PerplexicaNewsConnector(
        base_url="http://localhost:3001",
        queries=["bitcoin news"],
        query_fn=fail_query,
    )

    assert connector.fetch_latest() == []
