from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class MemoryRecorder(Protocol):
    def remember(self, text: str, important: bool = False) -> None: ...


@dataclass(slots=True)
class NullMemoryRecorder:
    def remember(self, text: str, important: bool = False) -> None:
        return


@dataclass(slots=True)
class AgentMemoryRecorder:
    agent_name: str
    _client: object | None = field(default=None, init=False, repr=False)

    def remember(self, text: str, important: bool = False) -> None:
        if self._client is None:
            self._client = self._build_client()
        if self._client is None:
            return
        try:
            self._client.remember(text, important=important)
        except Exception:
            return

    def _build_client(self):
        try:
            from memory.agent_memory import AgentMemory

            return AgentMemory(self.agent_name)
        except Exception:
            return None
