from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from urllib import request
import json


@dataclass(frozen=True)
class QdrantRetentionPolicy:
    collection: str
    ttl_days: int
    prune_batch_size: int = 1000


def _default_post(url: str, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def apply_qdrant_retention_policy(
    *,
    qdrant_url: str,
    policy: QdrantRetentionPolicy,
    post_fn: Callable[[str, dict[str, Any], float], dict[str, Any]] = _default_post,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    endpoint = qdrant_url.rstrip("/") + f"/collections/{policy.collection}/points/delete"

    payload = {
        "filter": {
            "must": [
                {
                    "key": "created_at_epoch",
                    "range": {"lt": f"now-{policy.ttl_days}d"},
                }
            ]
        },
        "limit": policy.prune_batch_size,
    }

    try:
        result = post_fn(endpoint, payload, timeout_seconds)
        return {
            "ok": True,
            "collection": policy.collection,
            "ttl_days": policy.ttl_days,
            "response": result,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "collection": policy.collection,
            "ttl_days": policy.ttl_days,
            "error": str(exc),
        }
