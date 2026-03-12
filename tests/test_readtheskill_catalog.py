from datetime import datetime, timezone

from agents.research.readtheskill_catalog import readtheskill_crypto_documents, readtheskill_crypto_knowledge_base
from agents.research.skill_factory import ArtifactPromotionPolicy, ArtifactVerification, SkillFactory, evaluate_artifact_promotion


class InMemoryRegistry:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.items.append(payload)


def test_readtheskill_catalog_has_crypto_documents():
    docs = readtheskill_crypto_documents()
    assert len(docs) >= 8
    assert any("kelly" in d.title.lower() or "kelly" in d.content.lower() for d in docs)


def test_readtheskill_knowledge_base_feeds_skill_factory():
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=readtheskill_crypto_knowledge_base(), registry=registry)
    report = factory.run(query="crypto risk execution", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=5)

    assert len(report.proposals) > 0
    assert registry.items and registry.items[0]["event"] == "generated_artifact"

    decision = evaluate_artifact_promotion(
        report.proposals[0],
        verification=ArtifactVerification(
            checks_passed=False,
            tests_passed=False,
            citations_verified=False,
            reviewer_score=0.0,
        ),
        policy=ArtifactPromotionPolicy(),
    )
    assert decision.accepted is False
