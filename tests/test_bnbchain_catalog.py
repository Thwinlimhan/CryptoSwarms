from datetime import datetime, timezone

from agents.research.bnbchain_catalog import bnbchain_skill_documents, bnbchain_skill_knowledge_base
from agents.research.skill_factory import ArtifactPromotionPolicy, ArtifactVerification, SkillFactory, evaluate_artifact_promotion


class InMemoryRegistry:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.items.append(payload)


def test_bnbchain_catalog_has_expected_docs():
    docs = bnbchain_skill_documents()
    assert len(docs) >= 5
    assert any("greenfield" in d.title.lower() or "greenfield" in d.content.lower() for d in docs)
    assert any("erc-8004" in d.title.lower() or "erc8004" in d.content.lower() for d in docs)


def test_bnbchain_knowledge_base_feeds_skill_factory_with_gated_output():
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=bnbchain_skill_knowledge_base(), registry=registry)
    report = factory.run(query="bnbchain mcp tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=6)

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
