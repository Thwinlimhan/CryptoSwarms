"""Exchange Rate Limiter — token bucket rate limiting for all exchange APIs.

Prevents exchange bans and API lockouts by enforcing per-endpoint rate limits
using a token bucket algorithm.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("swarm.adapters.rate_limiter")


class TokenBucket:
    """Token bucket rate limiter.

    Allows `capacity` requests per `refill_seconds`.
    Tokens are refilled continuously.
    """

    def __init__(self, capacity: int, refill_seconds: float) -> None:
        self.capacity = capacity
        self.refill_seconds = refill_seconds
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.capacity / self.refill_seconds)
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.

        Returns:
            Time waited in seconds (0.0 if no wait was needed).
        """
        waited = 0.0
        async with self._lock:
            self._refill()
            while self.tokens < tokens:
                deficit = tokens - self.tokens
                wait_time = deficit * (self.refill_seconds / self.capacity)
                waited += wait_time
                await asyncio.sleep(wait_time)
                self._refill()
            self.tokens -= tokens
        return waited

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self.tokens


# Pre-configured rate limits per exchange endpoint
DEFAULT_LIMITS: dict[str, tuple[int, float]] = {
    # Binance: 1200 requests per minute for market data
    "binance_ticker": (1200, 60.0),
    "binance_klines": (1200, 60.0),
    "binance_depth": (1200, 60.0),
    "binance_order": (100, 10.0),  # 10 orders per second
    "binance_account": (600, 60.0),
    # Hyperliquid: 600 requests per minute for info endpoints
    "hyperliquid_info": (600, 60.0),
    "hyperliquid_order": (200, 60.0),
    "hyperliquid_meta": (600, 60.0),
    # Common
    "default": (120, 60.0),
}


class ExchangeRateLimiter:
    """Centralized rate limiter for all exchange API calls.

    Manages per-endpoint token buckets and provides async acquire/wait
    before making any exchange API call.
    """

    def __init__(
        self,
        custom_limits: dict[str, tuple[int, float]] | None = None,
    ) -> None:
        limits = {**DEFAULT_LIMITS}
        if custom_limits:
            limits.update(custom_limits)

        self.limits: dict[str, TokenBucket] = {
            endpoint: TokenBucket(capacity, refill_secs)
            for endpoint, (capacity, refill_secs) in limits.items()
        }
        self._stats: dict[str, int] = {}

    async def acquire(self, endpoint: str, tokens: int = 1) -> float:
        """Acquire rate limit tokens for an endpoint.

        Args:
            endpoint: The API endpoint identifier (e.g., "binance_ticker").
            tokens: Number of tokens to consume (default 1).

        Returns:
            Time waited in seconds.
        """
        bucket = self.limits.get(endpoint)
        if bucket is None:
            bucket = self.limits.get("default")
        if bucket is None:
            return 0.0

        waited = await bucket.acquire(tokens)
        self._stats[endpoint] = self._stats.get(endpoint, 0) + 1

        if waited > 0.1:
            logger.warning(
                "Rate limited on %s: waited %.2fs", endpoint, waited,
            )
        return waited

    def get_stats(self) -> dict[str, Any]:
        """Return rate limiting statistics."""
        return {
            "requests_by_endpoint": dict(self._stats),
            "available_tokens": {
                endpoint: round(bucket.available_tokens, 1)
                for endpoint, bucket in self.limits.items()
            },
        }
