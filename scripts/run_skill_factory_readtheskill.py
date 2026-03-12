from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agents.research.readtheskill_catalog import readtheskill_crypto_knowledge_base
from agents.research.skill_factory import (
    ArtifactPromotionPolicy,
    ArtifactVerification,
    SkillFactory,
    evaluate_artifact_promotion,
)


class PrintRegistry:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.events.append(payload)
        print(json.dumps(payload, indent=2))


def main() -> None:
    registry = PrintRegistry()
    factory = SkillFactory(knowledge_base=readtheskill_crypto_knowledge_base(), registry=registry)
    report = factory.run(query="crypto execution risk bayes kelly", now=datetime.now(timezone.utc), max_artifacts=12)

    verification = ArtifactVerification(
        checks_passed=False,
        tests_passed=False,
        citations_verified=False,
        reviewer_score=0.0,
    )
    policy = ArtifactPromotionPolicy()

    decisions = [
        {
            "artifact_id": artifact.artifact_id,
            "name": artifact.name,
            "accepted": evaluate_artifact_promotion(artifact, verification=verification, policy=policy).accepted,
            "quality_score": artifact.quality_score,
        }
        for artifact in report.proposals
    ]

    out_dir = Path("artifacts") / "skill_factory" / "readtheskill"
    written = factory.write_promoted_artifacts(
        out_dir=out_dir,
        artifacts=report.proposals,
        verification=verification,
        policy=policy,
    )

    print("\n=== ReadTheSkill Factory summary ===")
    print(
        json.dumps(
            {
                "run_id": report.run_id,
                "generated_at": report.generated_at.isoformat(),
                "proposals": len(report.proposals),
                "promotion_state": "pending_verification",
                "decisions": decisions,
                "written_artifacts": [str(path) for path in written],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
