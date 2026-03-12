import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

from cryptoswarms.adapters.redis_queue import redis_from_url
from cryptoswarms.execution_guard import IntentPayload

logger = logging.getLogger(__name__)


class AbstractQueue(ABC):
    @abstractmethod
    async def push(self, queue_name: str, payload: dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def pop(self, queue_name: str, timeout: int = 0) -> dict[str, Any] | None:
        pass


class RedisQueue(AbstractQueue):
    def __init__(self, redis_url: str):
        self.client = redis_from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def push(self, queue_name: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload)
        await self.client.lpush(queue_name, data)

    async def pop(self, queue_name: str, timeout: int = 0) -> dict[str, Any] | None:
        result = await self.client.brpop(queue_name, timeout=timeout)
        if result:
            _, data = result
            return json.loads(data)
        return None

    async def close(self) -> None:
        await self.client.aclose()


class LocalFallbackQueue(AbstractQueue):
    """Fallback in-process queue for local testing when Redis is down."""

    def __init__(self) -> None:
        import asyncio
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    def _get_queue(self, queue_name: str) -> "asyncio.Queue[dict[str, Any]]":
        import asyncio
        if queue_name not in self._queues:
            self._queues[queue_name] = asyncio.Queue()
        return self._queues[queue_name]

    async def push(self, queue_name: str, payload: dict[str, Any]) -> None:
        await self._get_queue(queue_name).put(payload)

    async def pop(self, queue_name: str, timeout: int = 0) -> dict[str, Any] | None:
        import asyncio
        q = self._get_queue(queue_name)
        if timeout <= 0:
            try:
                return q.get_nowait()
            except asyncio.QueueEmpty:
                return None
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


async def get_queue_adapter(redis_url: str) -> AbstractQueue:
    client = redis_from_url(redis_url)
    try:
        is_ok = await client.ping()
        if is_ok:
            return RedisQueue(redis_url)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {redis_url}: {e}. Falling back to in-memory queue.")
    finally:
        await client.aclose()

    return LocalFallbackQueue()
