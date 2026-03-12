from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from agents.research.security_controls import filter_credentials


@dataclass(frozen=True)
class SkillArtifact:
    skill_id: str
    name: str
    content: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SkillAuditEvent:
    skill_id: str
    actor: str
    action: str
    detail: str
    timestamp: datetime


class SkillHub:
    def __init__(self) -> None:
        self._skills: dict[str, SkillArtifact] = {}
        self._audit: list[SkillAuditEvent] = []

    def create_skill(self, *, skill_id: str, name: str, content: str, actor: str) -> SkillArtifact:
        now = datetime.now(timezone.utc)
        artifact = SkillArtifact(
            skill_id=skill_id,
            name=name,
            content=filter_credentials(text=content),
            version=1,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        self._skills[skill_id] = artifact
        self._log(skill_id=skill_id, actor=actor, action="create", detail=f"v{artifact.version}")
        return artifact

    def patch_skill(self, *, skill_id: str, patch_text: str, actor: str) -> SkillArtifact:
        current = self._require(skill_id)
        updated = SkillArtifact(
            skill_id=current.skill_id,
            name=current.name,
            content=current.content + "\n" + filter_credentials(text=patch_text),
            version=current.version + 1,
            status=current.status,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._skills[skill_id] = updated
        self._log(skill_id=skill_id, actor=actor, action="patch", detail=f"v{updated.version}")
        return updated

    def edit_skill(self, *, skill_id: str, new_content: str, actor: str) -> SkillArtifact:
        current = self._require(skill_id)
        updated = SkillArtifact(
            skill_id=current.skill_id,
            name=current.name,
            content=filter_credentials(text=new_content),
            version=current.version + 1,
            status=current.status,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._skills[skill_id] = updated
        self._log(skill_id=skill_id, actor=actor, action="edit", detail=f"v{updated.version}")
        return updated

    def submit_to_hub(self, *, skill_id: str, actor: str) -> SkillArtifact:
        current = self._require(skill_id)
        updated = SkillArtifact(
            skill_id=current.skill_id,
            name=current.name,
            content=current.content,
            version=current.version,
            status="pending_review",
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._skills[skill_id] = updated
        self._log(skill_id=skill_id, actor=actor, action="submit", detail="pending_review")
        return updated

    def approve_skill(self, *, skill_id: str, actor: str) -> SkillArtifact:
        current = self._require(skill_id)
        updated = SkillArtifact(
            skill_id=current.skill_id,
            name=current.name,
            content=current.content,
            version=current.version,
            status="approved",
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._skills[skill_id] = updated
        self._log(skill_id=skill_id, actor=actor, action="approve", detail="approved")
        return updated

    def get_skill(self, skill_id: str) -> SkillArtifact | None:
        return self._skills.get(skill_id)

    def audit_events(self, skill_id: str | None = None) -> list[SkillAuditEvent]:
        if skill_id is None:
            return list(self._audit)
        return [x for x in self._audit if x.skill_id == skill_id]

    def _require(self, skill_id: str) -> SkillArtifact:
        item = self._skills.get(skill_id)
        if item is None:
            raise ValueError(f"unknown skill_id: {skill_id}")
        return item

    def _log(self, *, skill_id: str, actor: str, action: str, detail: str) -> None:
        self._audit.append(
            SkillAuditEvent(
                skill_id=skill_id,
                actor=actor,
                action=action,
                detail=detail,
                timestamp=datetime.now(timezone.utc),
            )
        )
