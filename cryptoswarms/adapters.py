from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RedisKeyValueStore:
    """Concrete key/value adapter backed by a Redis-compatible client."""

    client: Any

    def set(self, key: str, value: str) -> None:
        self.client.set(key, value)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.client.setex(key, ttl_seconds, value)

    def get(self, key: str) -> str | None:
        value = self.client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)


@dataclass
class PostgresSqlExecutor:
    """Concrete SQL adapter backed by a DB-API2 compatible connection."""

    connection: Any

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        with self.connection.cursor() as cur:
            cur.execute(sql, params)
        self.connection.commit()

    def fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
        with self.connection.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return list(rows)
