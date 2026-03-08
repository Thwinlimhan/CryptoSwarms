from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from memory.runtime_memory import MemoryRecorder, NullMemoryRecorder


@dataclass(frozen=True)
class ResearchItem:
    source: str
    title: str
    content: str
    url: str
    published_at: datetime


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


@dataclass(frozen=True)
class ResearchSignal:
    hypothesis_id: str
    symbol: str
    confidence: float
    sentiment: SentimentResult
    source: str
    provenance: dict[str, str]
    created_at: datetime


class NewsSourceConnector(Protocol):
    def fetch_latest(self) -> list[ResearchItem]: ...


class HypothesisQueue(Protocol):
    def publish(self, payload: dict[str, object]) -> None: ...


POSITIVE_TOKENS = {"breakout", "adoption", "approval", "bullish", "surge", "inflow"}
NEGATIVE_TOKENS = {"hack", "exploit", "ban", "lawsuit", "liquidation", "bearish"}


def score_sentiment(text: str) -> SentimentResult:
    lower = text.lower()
    pos = sum(1 for token in POSITIVE_TOKENS if token in lower)
    neg = sum(1 for token in NEGATIVE_TOKENS if token in lower)
    raw = pos - neg
    score = max(-1.0, min(1.0, raw / 3.0))
    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"
    return SentimentResult(label=label, score=round(score, 4))


class StaticNewsConnector:
    def fetch_latest(self) -> list[ResearchItem]:
        now = datetime.now(timezone.utc)
        return [
            ResearchItem(
                source="cointelegraph",
                title="Bitcoin breakout as ETF inflow rises",
                content="Bitcoin sees breakout momentum with strong ETF inflow.",
                url="https://example.com/bitcoin-breakout",
                published_at=now,
            )
        ]


class MinimalResearchPipeline:
    def __init__(self, connector: NewsSourceConnector, queue: HypothesisQueue, memory_recorder: MemoryRecorder | None = None) -> None:
        self._connector = connector
        self._queue = queue
        self._memory = memory_recorder or NullMemoryRecorder()

    def run(self, symbol: str = "BTCUSDT") -> list[ResearchSignal]:
        emitted: list[ResearchSignal] = []
        for index, item in enumerate(self._connector.fetch_latest()):
            sentiment = score_sentiment(item.title + " " + item.content)
            confidence = 0.5 + max(0.0, sentiment.score) * 0.4
            signal = ResearchSignal(
                hypothesis_id=f"research-{symbol.lower()}-{index}",
                symbol=symbol,
                confidence=round(confidence, 4),
                sentiment=sentiment,
                source=item.source,
                provenance={"title": item.title, "url": item.url, "published_at": item.published_at.isoformat()},
                created_at=datetime.now(timezone.utc),
            )
            self._queue.publish(
                {
                    "hypothesis_id": signal.hypothesis_id,
                    "symbol": signal.symbol,
                    "confidence": signal.confidence,
                    "sentiment": signal.sentiment.label,
                    "source": signal.source,
                    "provenance": signal.provenance,
                }
            )
            self._memory.remember(
                f"research signal={signal.hypothesis_id} symbol={signal.symbol} source={signal.source} sentiment={signal.sentiment.label}",
                important=signal.confidence >= 0.65,
            )
            emitted.append(signal)
        return emitted
