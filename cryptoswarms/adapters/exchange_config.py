"""Exchange Config — testnet/mainnet endpoint configuration for all exchanges.

Provides a single source of truth for exchange API endpoints,
enabling safe development on testnets.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.adapters.exchange_config")


@dataclass
class EndpointConfig:
    """REST and WebSocket endpoints for a single exchange mode."""
    rest_url: str
    ws_url: str
    api_version: str = ""


# Pre-configured exchange endpoints
EXCHANGE_ENDPOINTS: dict[str, dict[str, EndpointConfig]] = {
    "binance": {
        "live": EndpointConfig(
            rest_url="https://api.binance.com",
            ws_url="wss://stream.binance.com:9443/ws",
            api_version="v3",
        ),
        "testnet": EndpointConfig(
            rest_url="https://testnet.binance.vision",
            ws_url="wss://testnet.binance.vision/ws",
            api_version="v3",
        ),
    },
    "binance_futures": {
        "live": EndpointConfig(
            rest_url="https://fapi.binance.com",
            ws_url="wss://fstream.binance.com/ws",
            api_version="v1",
        ),
        "testnet": EndpointConfig(
            rest_url="https://testnet.binancefuture.com",
            ws_url="wss://stream.binancefuture.com/ws",
            api_version="v1",
        ),
    },
    "hyperliquid": {
        "live": EndpointConfig(
            rest_url="https://api.hyperliquid.xyz",
            ws_url="wss://api.hyperliquid.xyz/ws",
        ),
        "testnet": EndpointConfig(
            rest_url="https://api.hyperliquid-testnet.xyz",
            ws_url="wss://api.hyperliquid-testnet.xyz/ws",
        ),
    },
}


class ExchangeConfig:
    """Centralized exchange endpoint configuration.

    Provides proper endpoint URLs for all supported exchanges
    in both live and testnet modes.
    """

    def __init__(
        self,
        exchange: str,
        mode: str = "testnet",
        custom_endpoints: dict[str, dict[str, EndpointConfig]] | None = None,
    ) -> None:
        if mode not in ("live", "testnet"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'live' or 'testnet'.")

        self.exchange = exchange.lower()
        self.mode = mode

        endpoints = custom_endpoints or EXCHANGE_ENDPOINTS
        exchange_config = endpoints.get(self.exchange)
        if exchange_config is None:
            raise ValueError(
                f"Unknown exchange '{self.exchange}'. "
                f"Supported: {list(endpoints.keys())}"
            )

        config = exchange_config.get(self.mode)
        if config is None:
            raise ValueError(
                f"No {self.mode} config for '{self.exchange}'. "
                f"Available modes: {list(exchange_config.keys())}"
            )

        self._config = config
        logger.info(
            "Exchange config initialized: %s (%s) → %s",
            self.exchange, self.mode, self._config.rest_url,
        )

    @property
    def rest_url(self) -> str:
        return self._config.rest_url

    @property
    def ws_url(self) -> str:
        return self._config.ws_url

    @property
    def api_version(self) -> str:
        return self._config.api_version

    @property
    def is_testnet(self) -> bool:
        return self.mode == "testnet"

    def get_endpoint(self, path: str) -> str:
        """Construct a full API endpoint URL."""
        base = self.rest_url.rstrip("/")
        if self.api_version:
            return f"{base}/api/{self.api_version}/{path.lstrip('/')}"
        return f"{base}/{path.lstrip('/')}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange": self.exchange,
            "mode": self.mode,
            "rest_url": self.rest_url,
            "ws_url": self.ws_url,
            "api_version": self.api_version,
        }
