from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryDagNode:
    node_id: str
    node_type: str
    topic: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryDagEdge:
    from_node_id: str
    to_node_id: str


class MemoryDag:
    def __init__(self) -> None:
        self._nodes: dict[str, MemoryDagNode] = {}
        self._edges: list[MemoryDagEdge] = []
        self._lock = asyncio.Lock()

    def add_node(
        self,
        *,
        node_type: str,
        topic: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> MemoryDagNode:
        ts = created_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        raw = f"{node_type}:{topic}:{content}:{ts.isoformat()}"
        node_id = sha1(raw.encode("utf-8")).hexdigest()[:12]
        node = MemoryDagNode(
            node_id=node_id,
            node_type=node_type,
            topic=topic,
            content=content,
            created_at=ts,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        return node

    async def async_add_node(
        self,
        *,
        node_type: str,
        topic: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> MemoryDagNode:
        """Thread-safe version of add_node using asyncio.Lock."""
        async with self._lock:
            return self.add_node(
                node_type=node_type,
                topic=topic,
                content=content,
                metadata=metadata,
                created_at=created_at,
            )

    def add_edge(self, *, from_node_id: str, to_node_id: str) -> None:
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            raise ValueError("both nodes must exist before linking")
        if self._reachable(start=to_node_id, target=from_node_id):
            raise ValueError("edge would create cycle")
        self._edges.append(MemoryDagEdge(from_node_id=from_node_id, to_node_id=to_node_id))

    async def async_add_edge(self, *, from_node_id: str, to_node_id: str) -> None:
        """Thread-safe version of add_edge using asyncio.Lock."""
        async with self._lock:
            self.add_edge(from_node_id=from_node_id, to_node_id=to_node_id)

    def get_node(self, node_id: str) -> MemoryDagNode | None:
        return self._nodes.get(node_id)

    def nodes(self) -> list[MemoryDagNode]:
        return sorted(self._nodes.values(), key=lambda x: x.created_at)

    def edges(self) -> list[MemoryDagEdge]:
        return list(self._edges)

    def children(self, node_id: str) -> list[MemoryDagNode]:
        out: list[MemoryDagNode] = []
        for edge in self._edges:
            if edge.from_node_id == node_id and edge.to_node_id in self._nodes:
                out.append(self._nodes[edge.to_node_id])
        return sorted(out, key=lambda x: x.created_at)

    def parents(self, node_id: str) -> list[MemoryDagNode]:
        out: list[MemoryDagNode] = []
        for edge in self._edges:
            if edge.to_node_id == node_id and edge.from_node_id in self._nodes:
                out.append(self._nodes[edge.from_node_id])
        return sorted(out, key=lambda x: x.created_at)

    def latest_by_topic(self, topic: str, limit: int = 20) -> list[MemoryDagNode]:
        rows = [n for n in self._nodes.values() if n.topic == topic]
        rows.sort(key=lambda x: x.created_at, reverse=True)
        return rows[: max(1, int(limit))]

    def _reachable(self, *, start: str, target: str) -> bool:
        stack = [start]
        seen: set[str] = set()
        while stack:
            node_id = stack.pop()
            if node_id == target:
                return True
            if node_id in seen:
                continue
            seen.add(node_id)
            for child in self.children(node_id):
                stack.append(child.node_id)
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type,
                    "topic": n.topic,
                    "content": n.content,
                    "created_at": n.created_at.isoformat(),
                    "metadata": n.metadata,
                }
                for n in self.nodes()
            ],
            "edges": [
                {
                    "from_node_id": e.from_node_id,
                    "to_node_id": e.to_node_id,
                }
                for e in self.edges()
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryDag":
        dag = cls()
        for raw in payload.get("nodes", []):
            node_id = str(raw.get("node_id", ""))
            if not node_id:
                continue
            try:
                created_at = datetime.fromisoformat(str(raw.get("created_at")))
            except Exception:
                continue
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            dag._nodes[node_id] = MemoryDagNode(
                node_id=node_id,
                node_type=str(raw.get("node_type", "unknown")),
                topic=str(raw.get("topic", "")),
                content=str(raw.get("content", "")),
                created_at=created_at,
                metadata=dict(raw.get("metadata") or {}),
            )

        for raw in payload.get("edges", []):
            from_node_id = str(raw.get("from_node_id", ""))
            to_node_id = str(raw.get("to_node_id", ""))
            if not from_node_id or not to_node_id:
                continue
            if from_node_id in dag._nodes and to_node_id in dag._nodes:
                dag._edges.append(MemoryDagEdge(from_node_id=from_node_id, to_node_id=to_node_id))
        return dag

    def save_json(self, path: str | Path) -> None:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "MemoryDag":
        in_path = Path(path)
        if not in_path.exists():
            return cls()
        try:
            payload = json.loads(in_path.read_text(encoding="utf-8"))
        except Exception:
            return cls()
        if not isinstance(payload, dict):
            return cls()
        return cls.from_dict(payload)

