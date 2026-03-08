from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    content: str
    source: str
    run_id: str
    created_at: datetime


@dataclass(frozen=True)
class MemoryQualityReport:
    duplicate_ids: list[str]
    stale_ids: list[str]
    missing_traceability_ids: list[str]


def enforce_retention(items: list[MemoryItem], *, now: datetime, max_age_days: int) -> list[MemoryItem]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    return [item for item in items if item.created_at >= cutoff]


def assess_memory_quality(items: list[MemoryItem], *, now: datetime, stale_after_days: int = 30) -> MemoryQualityReport:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    stale_cutoff = now - timedelta(days=stale_after_days)

    seen_content: dict[str, str] = {}
    duplicate_ids: list[str] = []
    stale_ids: list[str] = []
    missing_traceability_ids: list[str] = []

    for item in items:
        normalized = " ".join(item.content.lower().split())
        first_id = seen_content.get(normalized)
        if first_id is None:
            seen_content[normalized] = item.memory_id
        else:
            duplicate_ids.append(item.memory_id)

        if item.created_at < stale_cutoff:
            stale_ids.append(item.memory_id)

        if not item.source.strip() or not item.run_id.strip():
            missing_traceability_ids.append(item.memory_id)

    return MemoryQualityReport(
        duplicate_ids=duplicate_ids,
        stale_ids=stale_ids,
        missing_traceability_ids=missing_traceability_ids,
    )
