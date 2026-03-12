import pytest
from datetime import datetime, timezone

from agents.research.research_factory import KnowledgeBase, KnowledgeDocument
from agents.research.skill_factory import (
    ArtifactPromotionPolicy,
    ArtifactVerification,
    SkillFactory,
    evaluate_artifact_promotion,
)


class InMemoryRegistry:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.items.append(payload)


def _knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(
        documents=[
            KnowledgeDocument(
                doc_id="doc-1",
                title="Execution Validation Workflow",
                source="paper",
                content="Build validation and execution risk controls into reusable workflows.",
                tags=("execution", "validation", "workflow"),
            ),
            KnowledgeDocument(
                doc_id="doc-2",
                title="Probability Helper Tools",
                source="article",
                content="Package analyst utilities for calibration and scenario analysis.",
                tags=("tools", "research"),
            ),
        ]
    )


def test_skill_factory_generates_artifacts_with_provenance():
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=_knowledge_base(), registry=registry)

    report = factory.run(query="execution validation tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=4)

    assert len(report.proposals) >= 1
    assert registry.items[0]["event"] == "generated_artifact"
    assert report.proposals[0].provenance_doc_ids


def test_promotion_gate_rejects_when_verification_fails():
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=_knowledge_base(), registry=registry)
    report = factory.run(query="execution validation tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=1)

    decision = evaluate_artifact_promotion(
        report.proposals[0],
        verification=ArtifactVerification(
            checks_passed=False,
            tests_passed=False,
            citations_verified=False,
            reviewer_score=0.4,
        ),
        policy=ArtifactPromotionPolicy(),
    )

    assert decision.accepted is False
    assert len(decision.reasons) >= 2


def test_write_promoted_artifacts_writes_only_accepted(tmp_path):
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=_knowledge_base(), registry=registry)
    report = factory.run(query="execution validation tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=2)

    written = factory.write_promoted_artifacts(
        out_dir=tmp_path,
        artifacts=report.proposals,
        verification=ArtifactVerification(
            checks_passed=True,
            tests_passed=True,
            citations_verified=True,
            reviewer_score=0.95,
        ),
        policy=ArtifactPromotionPolicy(),
    )

    assert written
    assert all(path.exists() for path in written)


def test_write_promoted_artifacts_skips_unverified_artifacts(tmp_path):
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=_knowledge_base(), registry=registry)
    report = factory.run(query="execution validation tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=2)

    written = factory.write_promoted_artifacts(
        out_dir=tmp_path,
        artifacts=report.proposals,
        verification=ArtifactVerification(
            checks_passed=False,
            tests_passed=False,
            citations_verified=False,
            reviewer_score=0.0,
        ),
        policy=ArtifactPromotionPolicy(),
    )

    assert written == []


def test_write_promoted_artifacts_blocks_non_idempotent_overwrite(tmp_path):
    registry = InMemoryRegistry()
    factory = SkillFactory(knowledge_base=_knowledge_base(), registry=registry)
    report = factory.run(query="execution validation tools", now=datetime(2026, 3, 8, tzinfo=timezone.utc), max_artifacts=1)

    factory.write_promoted_artifacts(
        out_dir=tmp_path,
        artifacts=report.proposals,
        verification=ArtifactVerification(
            checks_passed=True,
            tests_passed=True,
            citations_verified=True,
            reviewer_score=0.95,
        ),
        policy=ArtifactPromotionPolicy(),
    )

    rewritten = report.proposals[0].__class__(
        artifact_id=report.proposals[0].artifact_id,
        artifact_type=report.proposals[0].artifact_type,
        name=report.proposals[0].name,
        title=report.proposals[0].title,
        summary=report.proposals[0].summary,
        content=report.proposals[0].content + "\nmutation",
        provenance_doc_ids=report.proposals[0].provenance_doc_ids,
        generated_at=report.proposals[0].generated_at,
        quality_score=report.proposals[0].quality_score,
    )

    with pytest.raises(FileExistsError):
        factory.write_promoted_artifacts(
            out_dir=tmp_path,
            artifacts=[rewritten],
            verification=ArtifactVerification(
                checks_passed=True,
                tests_passed=True,
                citations_verified=True,
                reviewer_score=0.95,
            ),
            policy=ArtifactPromotionPolicy(),
        )
