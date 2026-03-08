from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import Iterable, Protocol

from agents.research.deerflow_pipeline import NewsSourceConnector, ResearchItem, score_sentiment


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    source: str
    content: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class HypothesisCandidate:
    hypothesis_id: str
    symbol: str
    title: str
    rationale: str
    confidence: float
    source_urls: tuple[str, ...]
    cited_docs: tuple[str, ...]
    strategy_id: str
    created_at: datetime


@dataclass(frozen=True)
class BacktestRequest:
    request_id: str
    hypothesis_id: str
    strategy_id: str
    symbol: str
    params: dict[str, float]
    priority: str
    created_at: datetime


@dataclass(frozen=True)
class FactoryRunReport:
    run_id: str
    generated_at: datetime
    fetched_items: int
    hypotheses_emitted: int
    backtest_requests: list[BacktestRequest]


class HypothesisQueue(Protocol):
    def publish(self, payload: dict[str, object]) -> None: ...


@dataclass(slots=True)
class KnowledgeBase:
    documents: list[KnowledgeDocument]

    def search(self, query: str, *, limit: int = 5) -> list[KnowledgeDocument]:
        tokens = {t.lower() for t in query.replace("-", " ").split() if t}
        if not tokens:
            return self.documents[:limit]

        scored: list[tuple[int, KnowledgeDocument]] = []
        for doc in self.documents:
            haystack = f"{doc.title} {doc.content} {' '.join(doc.tags)}".lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:limit]]


@dataclass(slots=True)
class ResearchFactory:
    connectors: list[NewsSourceConnector]
    knowledge_base: KnowledgeBase
    queue: HypothesisQueue
    strategy_universe: tuple[str, ...] = ("phase1-btc-breakout-15m",)

    def run(self, *, symbol: str = "BTCUSDT", max_hypotheses: int = 8, now: datetime | None = None) -> FactoryRunReport:
        ts = now or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        fetched = self._fetch_deduped_items(self.connectors)
        hypotheses: list[HypothesisCandidate] = []
        requests: list[BacktestRequest] = []

        for item in fetched:
            if len(hypotheses) >= max_hypotheses:
                break
            hypothesis = self._build_hypothesis(item=item, symbol=symbol, created_at=ts)
            hypotheses.append(hypothesis)
            request = self._build_backtest_request(hypothesis=hypothesis, created_at=ts)
            requests.append(request)
            self.queue.publish(
                {
                    "event": "research_hypothesis",
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "symbol": hypothesis.symbol,
                    "title": hypothesis.title,
                    "confidence": hypothesis.confidence,
                    "rationale": hypothesis.rationale,
                    "source_urls": list(hypothesis.source_urls),
                    "cited_docs": list(hypothesis.cited_docs),
                    "strategy_id": hypothesis.strategy_id,
                    "backtest_request": {
                        "request_id": request.request_id,
                        "params": request.params,
                        "priority": request.priority,
                    },
                    "created_at": ts.isoformat(),
                }
            )

        run_id = _stable_id(f"{symbol}:{ts.isoformat()}:{len(hypotheses)}")
        return FactoryRunReport(
            run_id=run_id,
            generated_at=ts,
            fetched_items=len(fetched),
            hypotheses_emitted=len(hypotheses),
            backtest_requests=requests,
        )

    def _build_hypothesis(self, *, item: ResearchItem, symbol: str, created_at: datetime) -> HypothesisCandidate:
        sentiment = score_sentiment(item.title + " " + item.content)
        related_docs = self.knowledge_base.search(item.title + " " + item.content, limit=3)
        confidence = round(0.45 + max(0.0, sentiment.score) * 0.35 + min(0.2, len(related_docs) * 0.05), 4)

        strategy_id = self.strategy_universe[0] if self.strategy_universe else "phase1-btc-breakout-15m"
        hypothesis_id = _stable_id(f"{item.source}:{item.url}:{symbol}")

        citations = tuple(doc.doc_id for doc in related_docs)
        rationale = (
            f"{item.title} | sentiment={sentiment.label}:{sentiment.score:.2f} | "
            f"docs={','.join(citations) if citations else 'none'}"
        )
        return HypothesisCandidate(
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            title=item.title,
            rationale=rationale,
            confidence=min(0.99, confidence),
            source_urls=(item.url,),
            cited_docs=citations,
            strategy_id=strategy_id,
            created_at=created_at,
        )

    def _build_backtest_request(self, *, hypothesis: HypothesisCandidate, created_at: datetime) -> BacktestRequest:
        request_id = _stable_id(f"bt:{hypothesis.hypothesis_id}:{created_at.isoformat()}")
        params = {
            "confidence_floor": round(max(0.55, hypothesis.confidence - 0.1), 4),
            "risk_scale": round(0.7 + hypothesis.confidence * 0.3, 4),
            "slippage_bps": 2.0,
        }
        priority = "high" if hypothesis.confidence >= 0.72 else "normal"
        return BacktestRequest(
            request_id=request_id,
            hypothesis_id=hypothesis.hypothesis_id,
            strategy_id=hypothesis.strategy_id,
            symbol=hypothesis.symbol,
            params=params,
            priority=priority,
            created_at=created_at,
        )

    @staticmethod
    def _fetch_deduped_items(connectors: Iterable[NewsSourceConnector]) -> list[ResearchItem]:
        merged: list[ResearchItem] = []
        seen: set[tuple[str, str]] = set()
        for connector in connectors:
            for item in connector.fetch_latest():
                key = (item.source, item.url)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        merged.sort(key=lambda x: x.published_at, reverse=True)
        return merged


def _stable_id(raw: str) -> str:
    return sha1(raw.encode("utf-8")).hexdigest()[:12]
