from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DocLike(Protocol):
    doc_id: str
    title: str
    content: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class LoadedChunk:
    doc_id: str
    title: str
    snippet: str
    score: int
    token_estimate: int


class ProgressiveSkillLoader:
    def __init__(self, *, token_budget: int = 1200) -> None:
        self.token_budget = max(100, int(token_budget))

    def load(self, *, query: str, documents: list[DocLike], per_doc_snippet_words: int = 60) -> list[LoadedChunk]:
        tokens = {t.lower() for t in query.replace("-", " ").split() if t}
        scored: list[tuple[int, DocLike]] = []

        for doc in documents:
            haystack = f"{doc.title} {doc.content} {' '.join(doc.tags)}".lower()
            score = sum(1 for t in tokens if t in haystack)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)

        used = 0
        out: list[LoadedChunk] = []
        for score, doc in scored:
            words = doc.content.split()
            snippet_words = words[:max(10, int(per_doc_snippet_words))]
            snippet = " ".join(snippet_words)
            token_estimate = max(1, len(snippet) // 4)
            if used + token_estimate > self.token_budget:
                break
            out.append(
                LoadedChunk(
                    doc_id=doc.doc_id,
                    title=doc.title,
                    snippet=snippet,
                    score=score,
                    token_estimate=token_estimate,
                )
            )
            used += token_estimate

        return out
