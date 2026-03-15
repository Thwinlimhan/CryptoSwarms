"""Exchange Error Handler — structured error handling for exchange API responses.

Translates raw exchange error codes into domain-specific exceptions,
preventing silent failures and enabling proper retry/recovery logic.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("swarm.adapters.exchange_errors")


# ── Domain Exceptions ────────────────────────────────────────────

class ExchangeError(Exception):
    """Base exception for all exchange errors."""

    def __init__(self, message: str, code: int | None = None, exchange: str = "unknown"):
        super().__init__(message)
        self.code = code
        self.exchange = exchange


class RateLimitExceeded(ExchangeError):
    """Exchange rate limit has been hit."""

    def __init__(self, retry_after: float = 60.0, exchange: str = "unknown"):
        super().__init__(
            f"Rate limit exceeded on {exchange}. Retry after {retry_after}s",
            code=429,
            exchange=exchange,
        )
        self.retry_after = retry_after


class OrderRejected(ExchangeError):
    """Exchange rejected the order."""

    def __init__(self, reason: str, code: int | None = None, exchange: str = "unknown"):
        super().__init__(f"Order rejected on {exchange}: {reason}", code=code, exchange=exchange)
        self.reason = reason


class InsufficientBalance(ExchangeError):
    """Insufficient balance to place the order."""

    def __init__(self, exchange: str = "unknown"):
        super().__init__(f"Insufficient balance on {exchange}", code=-2010, exchange=exchange)


class InvalidSymbol(ExchangeError):
    """The trading symbol is not valid."""

    def __init__(self, symbol: str, exchange: str = "unknown"):
        super().__init__(f"Invalid symbol '{symbol}' on {exchange}", exchange=exchange)
        self.symbol = symbol


class ExchangeUnavailable(ExchangeError):
    """Exchange is temporarily unavailable."""

    def __init__(self, exchange: str = "unknown"):
        super().__init__(f"{exchange} is temporarily unavailable", code=503, exchange=exchange)


class AuthenticationError(ExchangeError):
    """API key or signature is invalid."""

    def __init__(self, exchange: str = "unknown"):
        super().__init__(f"Authentication failed on {exchange}", code=401, exchange=exchange)


# ── Error Handler ────────────────────────────────────────────────

class ExchangeErrorHandler:
    """Handles exchange API error responses and raises domain-specific exceptions."""

    def handle_binance_error(self, response: dict[str, Any]) -> None:
        """Parse and raise Binance-specific errors.

        Binance error codes reference:
        https://binance-docs.github.io/apidocs/spot/en/#error-codes
        """
        code = response.get("code")
        msg = response.get("msg", "Unknown error")

        if code is None:
            return  # Not an error response

        if code == 429 or code == -1015:
            raise RateLimitExceeded(retry_after=60, exchange="binance")
        elif code == -2010:
            raise InsufficientBalance(exchange="binance")
        elif code == -1121:
            raise InvalidSymbol(msg, exchange="binance")
        elif code == -2015:
            raise AuthenticationError(exchange="binance")
        elif code == -1003:
            raise RateLimitExceeded(retry_after=300, exchange="binance")
        elif code in (-1000, -1001):
            raise ExchangeUnavailable(exchange="binance")
        elif code < 0:
            raise OrderRejected(msg, code=code, exchange="binance")

        logger.warning("Unhandled Binance code %d: %s", code, msg)

    def handle_hyperliquid_error(self, response: dict[str, Any]) -> None:
        """Parse and raise Hyperliquid-specific errors."""
        status = response.get("status")
        error = response.get("response", {})
        msg = ""

        if isinstance(error, dict):
            msg = error.get("type", "") or error.get("msg", "")
        elif isinstance(error, str):
            msg = error

        if status == "err":
            if "rate" in msg.lower() or "limit" in msg.lower():
                raise RateLimitExceeded(retry_after=30, exchange="hyperliquid")
            elif "insufficient" in msg.lower() or "margin" in msg.lower():
                raise InsufficientBalance(exchange="hyperliquid")
            elif "invalid" in msg.lower() and "symbol" in msg.lower():
                raise InvalidSymbol(msg, exchange="hyperliquid")
            else:
                raise OrderRejected(msg, exchange="hyperliquid")

    def handle_response(self, exchange: str, response: dict[str, Any]) -> None:
        """Route to the appropriate exchange error handler."""
        if exchange == "binance":
            self.handle_binance_error(response)
        elif exchange == "hyperliquid":
            self.handle_hyperliquid_error(response)
        else:
            # Generic error detection
            if response.get("error") or response.get("code", 0) < 0:
                raise ExchangeError(
                    str(response.get("error", response.get("msg", "Unknown error"))),
                    code=response.get("code"),
                    exchange=exchange,
                )
