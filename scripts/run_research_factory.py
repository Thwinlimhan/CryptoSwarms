from __future__ import annotations

import json
from datetime import datetime, timezone

from agents.research.deerflow_pipeline import StaticNewsConnector
from agents.research.research_factory import KnowledgeBase, KnowledgeDocument, ResearchFactory
from agents.research.stack_profiles import recommended_stack_profiles


class PrintQueue:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.events.append(payload)
        print(json.dumps(payload, indent=2))


def build_knowledge_base() -> KnowledgeBase:
    docs = [
        KnowledgeDocument(
            doc_id="book-advances-finml",
            title="Advances in Financial Machine Learning",
            source="book",
            content="Emphasize robust cross-validation, regime awareness, and leakage controls.",
            tags=("ml", "risk", "validation"),
        ),
        KnowledgeDocument(
            doc_id="paper-momentum-regimes",
            title="Regime-aware Crypto Momentum",
            source="paper",
            content="Momentum alpha decays in choppy regimes; require confidence filters and volatility scaling.",
            tags=("momentum", "regime", "crypto"),
        ),
        KnowledgeDocument(
            doc_id="paper-execution-impact",
            title="Market Impact in Electronic Trading",
            source="paper",
            content="Slippage and impact rise nonlinearly with size; cap participation and enforce impact guardrails.",
            tags=("execution", "slippage", "impact"),
        ),
    ]
    return KnowledgeBase(documents=docs)


def main() -> None:
    queue = PrintQueue()
    factory = ResearchFactory(
        connectors=[StaticNewsConnector()],
        knowledge_base=build_knowledge_base(),
        queue=queue,
        strategy_universe=("phase1-btc-breakout-15m",),
    )
    report = factory.run(symbol="BTCUSDT", max_hypotheses=5, now=datetime.now(timezone.utc))

    print("\n=== Factory run summary ===")
    print(
        json.dumps(
            {
                "run_id": report.run_id,
                "generated_at": report.generated_at.isoformat(),
                "fetched_items": report.fetched_items,
                "hypotheses_emitted": report.hypotheses_emitted,
                "backtest_requests": [
                    {
                        "request_id": req.request_id,
                        "hypothesis_id": req.hypothesis_id,
                        "strategy_id": req.strategy_id,
                        "priority": req.priority,
                    }
                    for req in report.backtest_requests
                ],
                "stack_profiles": [
                    {"name": p.name, "status": p.integration_status, "priority": p.priority}
                    for p in recommended_stack_profiles()
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
