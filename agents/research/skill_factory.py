from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Protocol

from agents.research.research_factory import KnowledgeBase, KnowledgeDocument
from cryptoswarms.immutable_artifacts import write_immutable_text


@dataclass(frozen=True)
class GeneratedArtifact:
    artifact_id: str
    artifact_type: str
    name: str
    title: str
    summary: str
    content: str
    provenance_doc_ids: tuple[str, ...]
    generated_at: datetime
    quality_score: float


@dataclass(frozen=True)
class ArtifactVerification:
    checks_passed: bool
    tests_passed: bool
    citations_verified: bool
    reviewer_score: float = 1.0


@dataclass(frozen=True)
class ArtifactPromotionPolicy:
    min_quality_score: float = 0.6
    min_reviewer_score: float = 0.7
    require_tests: bool = True
    require_citations: bool = True


@dataclass(frozen=True)
class ArtifactPromotionDecision:
    accepted: bool
    reasons: list[str]


@dataclass(frozen=True)
class SkillFactoryReport:
    run_id: str
    generated_at: datetime
    proposals: list[GeneratedArtifact]


class ArtifactRegistry(Protocol):
    def publish(self, payload: dict[str, object]) -> None: ...


@dataclass(slots=True)
class SkillFactory:
    knowledge_base: KnowledgeBase
    registry: ArtifactRegistry

    def run(
        self,
        *,
        query: str,
        now: datetime | None = None,
        max_artifacts: int = 6,
    ) -> SkillFactoryReport:
        ts = now or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        proposals: list[GeneratedArtifact] = []
        docs = self.knowledge_base.search(query, limit=max_artifacts)
        for doc in docs:
            artifact = self._propose_artifact(doc=doc, generated_at=ts)
            proposals.append(artifact)
            self.registry.publish(
                {
                    "event": "generated_artifact",
                    "artifact_id": artifact.artifact_id,
                    "artifact_type": artifact.artifact_type,
                    "name": artifact.name,
                    "title": artifact.title,
                    "summary": artifact.summary,
                    "provenance_doc_ids": list(artifact.provenance_doc_ids),
                    "quality_score": artifact.quality_score,
                    "generated_at": ts.isoformat(),
                }
            )

        run_id = _stable_id(f"skill-factory:{query}:{ts.isoformat()}:{len(proposals)}")
        return SkillFactoryReport(run_id=run_id, generated_at=ts, proposals=proposals)

    def write_promoted_artifacts(
        self,
        *,
        out_dir: Path,
        artifacts: list[GeneratedArtifact],
        verification: ArtifactVerification,
        policy: ArtifactPromotionPolicy = ArtifactPromotionPolicy(),
        immutable: bool = True,
    ) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for artifact in artifacts:
            decision = evaluate_artifact_promotion(artifact, verification=verification, policy=policy)
            if not decision.accepted:
                continue
            suffix = ".md" if artifact.artifact_type in {"skill", "playbook"} else ".txt"
            out_path = out_dir / f"{artifact.name}{suffix}"
            content = artifact.content + "\n"
            if immutable:
                write_immutable_text(out_path, content)
            else:
                out_path.write_text(content, encoding="utf-8")
            written.append(out_path)
        return written

    def _propose_artifact(self, *, doc: KnowledgeDocument, generated_at: datetime) -> GeneratedArtifact:
        artifact_type = _artifact_type_for_doc(doc)
        name = _slugify(doc.title)
        content = _render_artifact(doc=doc, artifact_type=artifact_type)
        quality_score = _score_document(doc)
        return GeneratedArtifact(
            artifact_id=_stable_id(f"{artifact_type}:{doc.doc_id}:{generated_at.isoformat()}"),
            artifact_type=artifact_type,
            name=name,
            title=doc.title,
            summary=f"Reusable {artifact_type} derived from {doc.source} knowledge: {doc.title}",
            content=content,
            provenance_doc_ids=(doc.doc_id,),
            generated_at=generated_at,
            quality_score=quality_score,
        )


def evaluate_artifact_promotion(
    artifact: GeneratedArtifact,
    *,
    verification: ArtifactVerification,
    policy: ArtifactPromotionPolicy = ArtifactPromotionPolicy(),
) -> ArtifactPromotionDecision:
    reasons: list[str] = []
    if artifact.quality_score < policy.min_quality_score:
        reasons.append(
            f"quality score below threshold: {artifact.quality_score:.3f} < {policy.min_quality_score:.3f}"
        )
    if policy.require_tests and not verification.tests_passed:
        reasons.append("verification tests not passed")
    if policy.require_citations and not verification.citations_verified:
        reasons.append("citations not verified")
    if not verification.checks_passed:
        reasons.append("artifact checks not passed")
    if verification.reviewer_score < policy.min_reviewer_score:
        reasons.append(
            f"reviewer score below threshold: {verification.reviewer_score:.3f} < {policy.min_reviewer_score:.3f}"
        )
    return ArtifactPromotionDecision(accepted=(len(reasons) == 0), reasons=reasons)


def _artifact_type_for_doc(doc: KnowledgeDocument) -> str:
    haystack = f"{doc.title} {doc.content} {' '.join(doc.tags)}".lower()
    if any(token in haystack for token in ("risk", "execution", "validation", "testing")):
        return "skill"
    if any(token in haystack for token in ("workflow", "playbook", "operations", "runbook")):
        return "playbook"
    return "tool_spec"


def _render_artifact(*, doc: KnowledgeDocument, artifact_type: str) -> str:
    heading = {
        "skill": "Skill",
        "playbook": "Playbook",
        "tool_spec": "Tool Spec",
    }[artifact_type]
    return "\n".join(
        [
            f"# {heading}: {doc.title}",
            "",
            f"- Source: `{doc.source}`",
            f"- Provenance doc id: `{doc.doc_id}`",
            f"- Tags: `{', '.join(doc.tags) if doc.tags else 'none'}`",
            "",
            "## Purpose",
            doc.content.strip(),
            "",
            "## Agent Usage",
            "Use this artifact only when the task directly matches the cited concept.",
            "Do not bypass verification, promotion, or risk controls because of this artifact.",
            "",
            "## Checklist",
            "- Confirm the artifact matches the active market/regime.",
            "- Attach provenance when using it in research or execution.",
            "- Route generated outputs through existing validation and promotion gates.",
        ]
    )


def _score_document(doc: KnowledgeDocument) -> float:
    tag_bonus = min(0.2, len(doc.tags) * 0.04)
    length_bonus = min(0.3, len(doc.content.split()) / 80.0)
    source_bonus = 0.15 if doc.source in {"paper", "book"} else 0.08
    return round(min(0.99, 0.35 + tag_bonus + length_bonus + source_bonus), 4)


def _stable_id(raw: str) -> str:
    return sha1(raw.encode("utf-8")).hexdigest()[:12]


def _slugify(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts[:8]) or "generated-artifact"
