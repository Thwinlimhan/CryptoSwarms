"""Exchange Circuit Breaker — prevents cascade failures from exchange issues.

Implements the circuit breaker pattern (CLOSED → OPEN → HALF_OPEN → CLOSED)
to protect the system from repeated exchange failures.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable, TypeVar

logger = logging.getLogger("swarm.resilience.circuit_breaker")

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, rejecting calls
    HALF_OPEN = "HALF_OPEN"  # Testing if recovery is possible


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted on an open circuit breaker."""

    def __init__(self, name: str, reset_at: float):
        remaining = max(0, reset_at - time.monotonic())
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. "
            f"Retry in {remaining:.0f}s"
        )
        self.name = name
        self.remaining_seconds = remaining


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    total_calls: int
    last_failure_at: datetime | None
    last_success_at: datetime | None
    times_opened: int
    consecutive_successes_in_half_open: int


class ExchangeCircuitBreaker:
    """Circuit breaker for exchange API calls.

    States:
    - CLOSED: Normal operation. Track failures.
    - OPEN: Too many failures. Reject all calls. Wait for timeout.
    - HALF_OPEN: Timeout elapsed. Allow one test call.
                 Success → CLOSED. Failure → OPEN.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        timeout: float = 300.0,
        half_open_max_calls: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._last_failure_time: float = 0
        self._last_failure_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._times_opened = 0
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current state, checking if OPEN should transition to HALF_OPEN."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0
                logger.info(
                    "Circuit breaker '%s': OPEN → HALF_OPEN (timeout elapsed)",
                    self.name,
                )
        return self._state

    async def call_exchange(
        self,
        exchange_fn: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute an exchange function through the circuit breaker.

        Args:
            exchange_fn: Async function to call.
            *args, **kwargs: Arguments for the function.

        Returns:
            Result of exchange_fn.

        Raises:
            CircuitBreakerOpenError: If the circuit is OPEN.
        """
        async with self._lock:
            current_state = self.state
            self._total_calls += 1

            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    self.name,
                    self._last_failure_time + self.timeout,
                )

        try:
            result = await exchange_fn(*args, **kwargs)
        except Exception as exc:
            await self._record_failure()
            raise
        else:
            await self._record_success()
            return result

    async def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self._last_failure_at = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN → back to OPEN
                self._state = CircuitState.OPEN
                self._times_opened += 1
                logger.warning(
                    "Circuit breaker '%s': HALF_OPEN → OPEN (failure during test)",
                    self.name,
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._times_opened += 1
                logger.warning(
                    "Circuit breaker '%s': CLOSED → OPEN (failures=%d >= threshold=%d)",
                    self.name, self._failure_count, self.failure_threshold,
                )

    async def _record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        async with self._lock:
            self._success_count += 1
            self._last_success_at = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(
                        "Circuit breaker '%s': HALF_OPEN → CLOSED (recovered)",
                        self.name,
                    )

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_successes = 0
        logger.info("Circuit breaker '%s' manually reset to CLOSED", self.name)

    @property
    def stats(self) -> CircuitBreakerStats:
        return CircuitBreakerStats(
            name=self.name,
            state=self.state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            total_calls=self._total_calls,
            last_failure_at=self._last_failure_at,
            last_success_at=self._last_success_at,
            times_opened=self._times_opened,
            consecutive_successes_in_half_open=self._half_open_successes,
        )


class CircuitBreakerRegistry:
    """Manages circuit breakers for multiple exchanges/endpoints."""

    def __init__(self) -> None:
        self._breakers: dict[str, ExchangeCircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 300.0,
    ) -> ExchangeCircuitBreaker:
        """Get an existing circuit breaker or create a new one."""
        if name not in self._breakers:
            self._breakers[name] = ExchangeCircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout=timeout,
            )
        return self._breakers[name]

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get stats for all circuit breakers."""
        return {name: cb.stats for name, cb in self._breakers.items()}
