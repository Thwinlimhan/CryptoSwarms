from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib import request

from agents.research.deerflow_pipeline import ResearchItem


def _default_query(base_url: str, query: str, timeout: float) -> dict[str, object]:
    endpoint = base_url.rstrip("/") + "/api/search"
    payload = json.dumps({"query": query}).encode("utf-8")
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    decoded = json.loads(raw)
    if isinstance(decoded, dict):
        return decoded
    return {"results": []}


@dataclass(slots=True)
class PerplexicaNewsConnector:
    base_url: str
    queries: list[str]
    timeout_seconds: float = 10.0
    query_fn: Callable[[str, str, float], dict[str, object]] = _default_query

    def fetch_latest(self) -> list[ResearchItem]:
        items: list[ResearchItem] = []
        for q in self.queries:
            try:
                payload = self.query_fn(self.base_url, q, self.timeout_seconds)
            except Exception:
                continue

            results = payload.get("results") if isinstance(payload, dict) else []
            if not isinstance(results, list):
                continue

            for result in results:
                if not isinstance(result, dict):
                    continue
                title = str(result.get("title") or q)
                content = str(result.get("snippet") or result.get("content") or "")
                url = str(result.get("url") or "")
                if not content and not url:
                    continue
                items.append(
                    ResearchItem(
                        source="perplexica",
                        title=title,
                        content=content,
                        url=url or "local://perplexica",
                        published_at=datetime.now(timezone.utc),
                    )
                )
        return items
