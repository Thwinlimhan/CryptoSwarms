from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from typing import Iterable, Protocol

from agents.research.deerflow_pipeline import NewsSourceConnector, ResearchItem, score_sentiment
from agents.research.progressive_loader import ProgressiveSkillLoader
from agents.research.security_controls import input_guardrail
from cryptoswarms.base_rate_registry import BaseRateRegistry, default_base_rate_registry
from cryptoswarms.bayesian_update import sentiment_likelihoods, sequential_bayes_update
from cryptoswarms.dag_recall import DagWalker
from cryptoswarms.decision_engine import OutcomeScenario, expected_value
from cryptoswarms.failure_ledger import FailureLedger
from cryptoswarms.fractional_kelly import empirical_fractional_kelly
from cryptoswarms.memory_dag import MemoryDag, MemoryDagNode


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
    prior_probability: float
    posterior_probability: float
    expected_value_after_costs_usd: float
    memory_context_node_ids: tuple[str, ...] = ()


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
    base_rate_registry: BaseRateRegistry | None = None
    failure_ledger: FailureLedger | None = None
    progressive_loader: ProgressiveSkillLoader = ProgressiveSkillLoader(token_budget=1200)
    memory_dag: MemoryDag | None = None
    memory_lookback_hours: int = 72
    memory_recall_max_nodes: int = 4
    memory_recall_token_budget: int = 500

    def run(self, *, symbol: str = "BTCUSDT", max_hypotheses: int = 8, now: datetime | None = None) -> FactoryRunReport:
        guard = input_guardrail(
            text=f"{symbol}:{max_hypotheses}",
            max_chars=64,
            banned_patterns=(" ", ";", "DROP", "DELETE"),
        )
        if not guard.allowed:
            raise ValueError(f"research input blocked: {guard.reason}")

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
            memory_node_id = self._record_hypothesis_memory(hypothesis=hypothesis, item=item, created_at=ts)
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
                    "decision_math": {
                        "prior_probability": hypothesis.prior_probability,
                        "posterior_probability": hypothesis.posterior_probability,
                        "expected_value_after_costs_usd": hypothesis.expected_value_after_costs_usd,
                    },
                    "memory": {
                        "context_node_ids": list(hypothesis.memory_context_node_ids),
                        "checkpoint_node_id": memory_node_id,
                    },
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
        chunks = self.progressive_loader.load(query=item.title + " " + item.content, documents=self.knowledge_base.documents)
        related_docs = [doc for doc in self.knowledge_base.documents if doc.doc_id in {c.doc_id for c in chunks}][:3]

        strategy_id = self.strategy_universe[0] if self.strategy_universe else "phase1-btc-breakout-15m"
        memory_context_nodes = self._recall_context_nodes(topic=strategy_id, now=created_at)
        memory_context_ids = tuple(node.node_id for node in memory_context_nodes)
        context_quality = 1.0
        if memory_context_nodes:
            context_quality = sum(float(node.metadata.get("provenance_confidence", 1.0)) for node in memory_context_nodes) / len(memory_context_nodes)

        registry = self.base_rate_registry or default_base_rate_registry()
        prior = registry.empirical_bayes_prior(strategy_id, fallback=0.52, pseudo_count=30)

        lt, lf = sentiment_likelihoods(sentiment.score)
        doc_likelihood_true = min(0.75, 0.52 + len(related_docs) * 0.05)
        doc_likelihood_false = max(0.35, 0.52 - len(related_docs) * 0.03)

        posterior = sequential_bayes_update(
            prior=prior,
            evidence=[
                (lt, lf),
                (doc_likelihood_true, doc_likelihood_false),
            ],
        )

        fail_rate = 0.0
        if self.failure_ledger is not None:
            fail_rate = self.failure_ledger.failure_rate(key=strategy_id, lookback_days=90)
        survivorship_penalty = min(0.2, fail_rate * 0.35)
        posterior_adjusted = max(0.001, min(0.999, posterior - survivorship_penalty))
        posterior_adjusted = max(0.001, min(0.999, posterior_adjusted * max(0.75, min(1.0, context_quality + 0.1))))

        ev = expected_value(
            scenarios=[
                OutcomeScenario(probability=posterior_adjusted, payoff_usd=25.0),
                OutcomeScenario(probability=1.0 - posterior_adjusted, payoff_usd=-20.0),
            ],
            fees_usd=2.0,
            slippage_usd=2.0,
        )

        hypothesis_id = _stable_id(f"{item.source}:{item.url}:{symbol}")
        citations = tuple(doc.doc_id for doc in related_docs)
        rationale = (
            f"{item.title} | sentiment={sentiment.label}:{sentiment.score:.2f} | "
            f"prior={prior:.2f}->post={posterior_adjusted:.2f} | "
            f"ev_net={ev.expected_value_after_costs_usd:.2f} | "
            f"docs={','.join(citations) if citations else 'none'} | "
            f"mem_ctx={len(memory_context_ids)} q={context_quality:.2f}"
        )

        return HypothesisCandidate(
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            title=item.title,
            rationale=rationale,
            confidence=round(posterior_adjusted, 4),
            source_urls=(item.url,),
            cited_docs=citations,
            strategy_id=strategy_id,
            created_at=created_at,
            prior_probability=round(prior, 4),
            posterior_probability=round(posterior_adjusted, 4),
            expected_value_after_costs_usd=round(ev.expected_value_after_costs_usd, 4),
            memory_context_node_ids=memory_context_ids,
        )

    def _build_backtest_request(self, *, hypothesis: HypothesisCandidate, created_at: datetime) -> BacktestRequest:
        request_id = _stable_id(f"bt:{hypothesis.hypothesis_id}:{created_at.isoformat()}")
        kelly_fraction = empirical_fractional_kelly(
            win_probability=hypothesis.posterior_probability,
            payoff_multiple=1.0,
            uncertainty_cv=0.35,
            kelly_fraction_multiplier=0.5,
            max_fraction=0.2,
        )
        params = {
            "confidence_floor": round(max(0.55, hypothesis.posterior_probability - 0.08), 4),
            "risk_scale": round(0.6 + 1.8 * kelly_fraction, 4),
            "slippage_bps": 2.0,
            "kelly_fraction": round(kelly_fraction, 6),
            "ev_after_costs_usd": round(hypothesis.expected_value_after_costs_usd, 4),
        }
        priority = "high" if hypothesis.posterior_probability >= 0.72 else "normal"
        return BacktestRequest(
            request_id=request_id,
            hypothesis_id=hypothesis.hypothesis_id,
            strategy_id=hypothesis.strategy_id,
            symbol=hypothesis.symbol,
            params=params,
            priority=priority,
            created_at=created_at,
        )

    def _recall_context_nodes(self, *, topic: str, now: datetime) -> list[MemoryDagNode]:
        if self.memory_dag is None:
            return []
        walker = DagWalker(self.memory_dag)
        recall = walker.recall(
            topic=topic,
            lookback_hours=self.memory_lookback_hours,
            max_nodes=self.memory_recall_max_nodes,
            token_budget=self.memory_recall_token_budget,
            now=now,
        )
        return recall.nodes

    def _record_hypothesis_memory(self, *, hypothesis: HypothesisCandidate, item: ResearchItem, created_at: datetime) -> str | None:
        if self.memory_dag is None:
            return None

        node = self.memory_dag.add_node(
            node_type="research_hypothesis",
            topic=hypothesis.strategy_id,
            content=hypothesis.rationale,
            created_at=created_at,
            metadata={
                "hypothesis_id": hypothesis.hypothesis_id,
                "symbol": hypothesis.symbol,
                "source_url": item.url,
                "confidence": hypothesis.confidence,
                "posterior_probability": hypothesis.posterior_probability,
                "expected_value_after_costs_usd": hypothesis.expected_value_after_costs_usd,
            },
        )
        for context_id in hypothesis.memory_context_node_ids:
            try:
                self.memory_dag.add_edge(from_node_id=context_id, to_node_id=node.node_id)
            except Exception:
                pass
        return node.node_id

    @staticmethod
    def _fetch_deduped_items(connectors: Iterable[NewsSourceConnector]) -> list[ResearchItem]:
        merged: list[ResearchItem] = []
        seen: set[tuple[str, str]] = set()

        connector_list = list(connectors)
        if len(connector_list) <= 1:
            iterator = ((c, c.fetch_latest()) for c in connector_list)
        else:
            with ThreadPoolExecutor(max_workers=min(8, len(connector_list))) as pool:
                futures = {pool.submit(c.fetch_latest): c for c in connector_list}
                iterator = []
                for future in as_completed(futures):
                    connector = futures[future]
                    try:
                        items = future.result()
                    except Exception:
                        items = []
                    iterator.append((connector, items))

        for _connector, items in iterator:
            for item in items:
                key = (item.source, item.url)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        merged.sort(key=lambda x: x.published_at, reverse=True)
        return merged


def _stable_id(raw: str) -> str:
    return sha1(raw.encode("utf-8")).hexdigest()[:12]



