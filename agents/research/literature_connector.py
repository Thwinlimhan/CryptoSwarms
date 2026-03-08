from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from agents.research.deerflow_pipeline import ResearchItem


@dataclass(frozen=True)
class LiteratureDoc:
    title: str
    abstract: str
    url: str
    published_at: datetime


@dataclass(slots=True)
class LiteratureConnector:
    fetch_fn: Callable[[], list[LiteratureDoc]]

    def fetch_latest(self) -> list[ResearchItem]:
        docs = self.fetch_fn()
        deduped = dedupe_literature_docs(docs)
        return [
            ResearchItem(
                source="literature",
                title=doc.title,
                content=doc.abstract,
                url=doc.url,
                published_at=doc.published_at.astimezone(timezone.utc),
            )
            for doc in deduped
        ]


def dedupe_literature_docs(docs: list[LiteratureDoc]) -> list[LiteratureDoc]:
    seen: set[tuple[str, str]] = set()
    output: list[LiteratureDoc] = []
    for doc in docs:
        key = (doc.title.strip().lower(), doc.url.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(doc)
    return output


def sample_literature_feed() -> list[LiteratureDoc]:
    now = datetime.now(timezone.utc)
    return [
        LiteratureDoc(
            title="Regime-aware crypto momentum",
            abstract="A framework for regime-aware momentum in digital assets.",
            url="https://arxiv.org/abs/1234.5678",
            published_at=now,
        ),
        LiteratureDoc(
            title="Regime-aware crypto momentum",
            abstract="Duplicate item",
            url="https://arxiv.org/abs/1234.5678",
            published_at=now,
        ),
    ]
