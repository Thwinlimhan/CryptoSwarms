from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib import request

from agents.research.deerflow_pipeline import ResearchItem


def _default_post_json(url: str, payload: dict[str, object], timeout: float) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    decoded = json.loads(raw)
    if isinstance(decoded, dict):
        return decoded
    return {"items": []}


@dataclass(slots=True)
class CamoufoxNewsConnector:
    base_url: str
    targets: list[str]
    timeout_seconds: float = 10.0
    post_json: Callable[[str, dict[str, object], float], dict[str, object]] = _default_post_json

    def fetch_latest(self) -> list[ResearchItem]:
        collected: list[ResearchItem] = []
        endpoint = self.base_url.rstrip("/") + "/extract"

        for target in self.targets:
            payload = {
                "url": target,
                "mode": "article",
                "wait_ms": 1200,
                "timeout_ms": int(self.timeout_seconds * 1000),
            }
            try:
                response = self.post_json(endpoint, payload, self.timeout_seconds)
            except Exception:
                continue

            items = response.get("items") if isinstance(response, dict) else []
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "")
                content = str(item.get("content") or item.get("text") or "")
                url = str(item.get("url") or target)
                published_raw = item.get("published_at")
                published = _parse_time(published_raw)

                if not title and not content:
                    continue

                collected.append(
                    ResearchItem(
                        source="camoufox",
                        title=title or "untitled",
                        content=content,
                        url=url,
                        published_at=published,
                    )
                )

        return collected


def _parse_time(raw: object) -> datetime:
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)
