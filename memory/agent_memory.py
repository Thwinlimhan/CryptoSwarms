"""Unified memory client for swarm agents.

This module centralizes access to fast semantic memory (Mem0/Qdrant)
and temporal memory (Graphiti/Neo4j).
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from graphiti_core import Graphiti
from mem0 import Memory

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
SGLANG_URL = os.getenv("SGLANG_URL", "http://localhost:30000/v1")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")


class AgentMemory:
    """Single API for memory operations used by all agents."""

    def __init__(self, agent_name: str) -> None:
        self.agent_id = agent_name
        self.fast = Memory(
            config={
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "url": QDRANT_URL,
                        "collection_name": "swarm_memory",
                    },
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "base_url": SGLANG_URL,
                        "model": "qwen3.5-4b",
                    },
                },
            }
        )
        self.graph = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASS)

    def remember(self, text: str, important: bool = False) -> None:
        """Store a memory item and optionally promote it to temporal memory."""
        self.fast.add(text, user_id=self.agent_id)
        if important:
            asyncio.run(
                self.graph.add_episode(
                    name=f"{self.agent_id}_{int(time.time())}",
                    episode_body=text,
                    source_description=f"Agent: {self.agent_id}",
                )
            )

    def recall(self, query: str, limit: int = 5) -> list[str]:
        """Return relevant fast-memory hits for a semantic query."""
        results: dict[str, Any] = self.fast.search(query, user_id=self.agent_id, limit=limit)
        return [result["memory"] for result in results.get("results", [])]

    def recall_history(self, query: str, num_results: int = 10) -> list[dict[str, Any]]:
        """Return temporal memory timeline for a query from Graphiti."""
        return asyncio.run(self.graph.search(query, num_results=num_results))

    def forget(self, query: str) -> int:
        """Delete all matching fast-memory entries and return deleted count."""
        results: dict[str, Any] = self.fast.search(query, user_id=self.agent_id)
        deleted = 0
        for result in results.get("results", []):
            memory_id = result.get("id")
            if memory_id:
                self.fast.delete(memory_id=memory_id)
                deleted += 1
        return deleted
