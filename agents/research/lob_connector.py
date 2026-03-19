"""
Hyperliquid Level-2 Order Book connector.
No authentication required.
Endpoint: POST https://api.hyperliquid.xyz/info
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


class HttpTransport(Protocol):
    def post(self, url: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class LOBSnapshot:
    symbol: str
    bids: list[tuple[float, float]]   # (price, size) sorted descending
    asks: list[tuple[float, float]]   # (price, size) sorted ascending
    timestamp_ms: int


@dataclass(slots=True)
class HyperliquidLOBConnector:
    """
    Fetches full L2 order book from Hyperliquid.
    Hyperliquid exposes top-of-book + N levels (typically 5-20 levels).
    """
    transport: HttpTransport
    base_url: str = "https://api.hyperliquid.xyz/info"

    def fetch_lob(self, symbol: str) -> LOBSnapshot:
        resp = self.transport.post(self.base_url, {
            "type": "l2Book",
            "coin": symbol,
        })
        levels = resp.get("levels", [[], []])
        bids = [(float(p["px"]), float(p["sz"])) for p in levels[0]]
        asks = [(float(p["px"]), float(p["sz"])) for p in levels[1]]
        return LOBSnapshot(
            symbol=symbol,
            bids=sorted(bids, reverse=True),
            asks=sorted(asks),
            timestamp_ms=resp.get("time", 0),
        )

    def fetch_recent_trades(self, symbol: str) -> list[dict]:
        """Fetch recent executed trades for tape OFI computation."""
        return self.transport.post(self.base_url, {
            "type": "trades",
            "coin": symbol,
        })