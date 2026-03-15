"""Signal Deduplicator — prevents duplicate signal processing.

Uses in-memory TTL cache (with optional Redis backend) to ensure
each unique signal combination is only processed once within a
configurable time window.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.dedup")


@dataclass
class DeduplicationStats:
    """Track deduplication statistics."""
    total_signals: int = 0
    deduplicated: int = 0
    passed: int = 0

    @property
    def dedup_rate(self) -> float:
        if self.total_signals == 0:
            return 0.0
        return self.deduplicated / self.total_signals


@dataclass
class CachedEntry:
    """Entry in the dedup cache with TTL."""
    key: str
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl_seconds


class SignalDeduplicator:
    """Prevents duplicate signal processing using dedup keys.

    Dedup key is generated from: symbol + timestamp + signal_type.
    Signals with the same key within the TTL window are filtered out.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        redis_client: Any | None = None,
        max_cache_size: int = 10_000,
    ) -> None:
        self._cache: dict[str, CachedEntry] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl_seconds
        self._redis = redis_client
        self._max_cache_size = max_cache_size
        self._stats = DeduplicationStats()

    @staticmethod
    def _build_dedup_key(symbol: str, timestamp: str, signal_type: str) -> str:
        raw = f"{symbol}:{timestamp}:{signal_type}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    async def process_signal(self, signal: dict[str, Any]) -> bool:
        """Return True if signal should be processed, False if duplicate.

        Args:
            signal: dict with keys 'symbol', 'timestamp', 'signal_type'

        Returns:
            True if the signal is new and should be processed.
        """
        symbol = str(signal.get("symbol", ""))
        timestamp = str(signal.get("timestamp", ""))
        signal_type = str(signal.get("signal_type", ""))

        dedup_key = self._build_dedup_key(symbol, timestamp, signal_type)

        async with self._lock:
            self._stats.total_signals += 1

            # Try Redis first if available
            if self._redis is not None:
                try:
                    result = await self._redis.set(
                        f"signal:{dedup_key}", "1", nx=True, ex=int(self._ttl)
                    )
                    if result:
                        self._stats.passed += 1
                        logger.debug("Signal %s accepted (Redis)", dedup_key[:8])
                        return True
                    else:
                        self._stats.deduplicated += 1
                        logger.debug("Signal %s deduplicated (Redis)", dedup_key[:8])
                        return False
                except Exception:
                    logger.warning("Redis dedup failed, falling back to memory")

            # In-memory fallback
            self._evict_expired()

            if dedup_key in self._cache:
                entry = self._cache[dedup_key]
                if not entry.is_expired:
                    self._stats.deduplicated += 1
                    logger.debug("Signal %s deduplicated (memory)", dedup_key[:8])
                    return False

            # Not a duplicate — register it
            self._cache[dedup_key] = CachedEntry(
                key=dedup_key,
                created_at=time.monotonic(),
                ttl_seconds=self._ttl,
            )
            self._stats.passed += 1
            logger.debug("Signal %s accepted (memory)", dedup_key[:8])
            return True

    def _evict_expired(self) -> None:
        """Remove expired entries and enforce max cache size."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired_keys:
            del self._cache[k]

        # If still over capacity, remove oldest entries
        if len(self._cache) >= self._max_cache_size:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at,
            )
            to_remove = sorted_keys[: len(self._cache) - self._max_cache_size + 1]
            for k in to_remove:
                del self._cache[k]

    @property
    def stats(self) -> DeduplicationStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = DeduplicationStats()
