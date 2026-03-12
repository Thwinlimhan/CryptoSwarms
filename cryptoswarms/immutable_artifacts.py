from __future__ import annotations

import json
from pathlib import Path


def write_immutable_text(path: Path, content: str, *, allow_idempotent: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if allow_idempotent and existing == content:
            return path
        raise FileExistsError(f"immutable artifact already exists: {path}")
    path.write_text(content, encoding="utf-8")
    return path


def write_immutable_json(path: Path, payload: dict[str, object], *, allow_idempotent: bool = True) -> Path:
    content = json.dumps(payload, indent=2)
    return write_immutable_text(path, content, allow_idempotent=allow_idempotent)
