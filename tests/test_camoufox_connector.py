from datetime import datetime, timezone

from agents.research.camoufox_connector import CamoufoxNewsConnector


def test_camoufox_connector_parses_items():
    def fake_post(url: str, payload: dict[str, object], timeout: float):
        return {
            "items": [
                {
                    "title": "ETF inflow sparks breakout",
                    "content": "BTC sees bullish inflow conditions.",
                    "url": payload["url"],
                    "published_at": "2026-03-08T00:00:00+00:00",
                }
            ]
        }

    connector = CamoufoxNewsConnector(
        base_url="http://localhost:8080",
        targets=["https://example.com/news"],
        post_json=fake_post,
    )

    items = connector.fetch_latest()
    assert len(items) == 1
    assert items[0].source == "camoufox"
    assert items[0].title.startswith("ETF")


def test_camoufox_connector_ignores_fetch_failures():
    def failing_post(url: str, payload: dict[str, object], timeout: float):
        raise RuntimeError("network error")

    connector = CamoufoxNewsConnector(
        base_url="http://localhost:8080",
        targets=["https://example.com/news"],
        post_json=failing_post,
    )

    assert connector.fetch_latest() == []
