from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from agents.research.deerflow_pipeline import ResearchItem


@dataclass(frozen=True)
class WhaleTransfer:
    token: str
    usd_value: float
    direction: str
    tx_hash: str
    time: datetime


@dataclass(slots=True)
class WhaleFlowConnector:
    fetch_fn: Callable[[], list[WhaleTransfer]]

    def fetch_latest(self) -> list[ResearchItem]:
        items: list[ResearchItem] = []
        for transfer in self.fetch_fn():
            direction = transfer.direction.lower()
            signal_word = "inflow" if direction == "in" else "outflow"
            content = (
                f"Whale {signal_word} detected: token={transfer.token} usd={transfer.usd_value:.2f} "
                f"tx={transfer.tx_hash}"
            )
            items.append(
                ResearchItem(
                    source="onchain_whale",
                    title=f"Whale {signal_word} {transfer.token}",
                    content=content,
                    url=f"https://etherscan.io/tx/{transfer.tx_hash}",
                    published_at=transfer.time.astimezone(timezone.utc),
                )
            )
        return items


def whale_confidence(usd_value: float) -> float:
    # Confidence saturates at 1.0 around $10M transfer size.
    if usd_value <= 0:
        return 0.0
    return min(1.0, round(0.4 + (usd_value / 10_000_000.0) * 0.6, 4))


def sample_whale_feed() -> list[WhaleTransfer]:
    now = datetime.now(timezone.utc)
    return [
        WhaleTransfer(token="BTC", usd_value=3_500_000.0, direction="in", tx_hash="abc123", time=now),
        WhaleTransfer(token="ETH", usd_value=8_000_000.0, direction="out", tx_hash="def456", time=now),
    ]
