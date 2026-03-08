from agents.research.onchain_connector import WhaleFlowConnector, WhaleTransfer, whale_confidence
from datetime import datetime, timezone


def test_whale_connector_emits_research_items():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)

    connector = WhaleFlowConnector(
        fetch_fn=lambda: [
            WhaleTransfer(token="BTC", usd_value=2_000_000, direction="in", tx_hash="abc", time=now)
        ]
    )

    items = connector.fetch_latest()
    assert len(items) == 1
    assert items[0].source == "onchain_whale"
    assert "Whale" in items[0].title


def test_whale_confidence_scales_with_size():
    assert whale_confidence(0) == 0.0
    assert whale_confidence(1_000_000) > 0.4
    assert whale_confidence(20_000_000) == 1.0
