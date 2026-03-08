from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImmutableAuditRecord:
    ts: str
    agent: str
    action: str
    run_id: str
    metadata: dict[str, Any]
    prev_hash: str
    hash: str


class ImmutableJsonlAuditLog:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def append(self, *, agent: str, action: str, run_id: str, metadata: dict[str, Any]) -> ImmutableAuditRecord:
        prev_hash = self._last_hash()
        ts = datetime.now(timezone.utc).isoformat()
        payload = {
            "ts": ts,
            "agent": agent,
            "action": action,
            "run_id": run_id,
            "metadata": metadata,
            "prev_hash": prev_hash,
        }
        record_hash = self._hash_payload(payload)
        record = {**payload, "hash": record_hash}

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

        return ImmutableAuditRecord(**record)

    def verify_chain(self) -> tuple[bool, str]:
        prev_hash = "GENESIS"
        with self._path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    return False, f"invalid json at line {line_no}"

                if record.get("prev_hash") != prev_hash:
                    return False, f"prev_hash mismatch at line {line_no}"

                payload = {
                    "ts": record.get("ts"),
                    "agent": record.get("agent"),
                    "action": record.get("action"),
                    "run_id": record.get("run_id"),
                    "metadata": record.get("metadata"),
                    "prev_hash": record.get("prev_hash"),
                }
                expected_hash = self._hash_payload(payload)
                if record.get("hash") != expected_hash:
                    return False, f"hash mismatch at line {line_no}"

                prev_hash = record["hash"]

        return True, "ok"

    def _last_hash(self) -> str:
        last_hash = "GENESIS"
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                last_hash = str(record.get("hash") or last_hash)
        return last_hash

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
