"""Senpi AI Hyperliquid smart-money feed connector.

Connects to the Senpi AI API to receive aggregated smart-money flow signals
from Hyperliquid perps. Returns normalized directional bias and divergence score.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SenpiTransport(Protocol):
    def get(self, url: str, params: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SmartMoneySignal:
    symbol: str
    direction: str          # "long" | "short" | "neutral"
    confidence: float       # 0.0–1.0
    net_flow_usd: float     # positive = net buy, negative = net sell
    funding_divergence: float   # spot vs perp funding diff (bps)
    large_print_detected: bool
    raw: dict[str, Any]


@dataclass(slots=True)
class SenpiHyperfeedConnector:
    """Fetches smart-money signals from the Senpi AI REST API.

    Args:
        base_url: Senpi API endpoint, e.g. "https://api.senpi.ai/v1"
        api_key: your Senpi API key (set via SENPI_API_KEY env var)
        transport: injectable HTTP transport
        large_print_threshold_usd: USD threshold to flag a large institutional print
    """
    base_url: str
    api_key: str
    transport: SenpiTransport
    large_print_threshold_usd: float = 500_000.0

    def fetch_signal(self, symbol: str, lookback_minutes: int = 60) -> SmartMoneySignal:
        resp = self.transport.get(
            self.base_url.rstrip("/") + "/hyperliquid/smart-money",
            {
                "symbol": symbol,
                "lookback_minutes": lookback_minutes,
                "api_key": self.api_key,
            },
        )
        net_flow = float(resp.get("net_flow_usd", 0.0))
        confidence = float(resp.get("confidence", 0.0))
        funding_div = float(resp.get("funding_divergence_bps", 0.0))
        large_print = abs(net_flow) >= self.large_print_threshold_usd

        if confidence < 0.4 or abs(net_flow) < 50_000:
            direction = "neutral"
        elif net_flow > 0:
            direction = "long"
        else:
            direction = "short"

        return SmartMoneySignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            net_flow_usd=net_flow,
            funding_divergence=funding_div,
            large_print_detected=large_print,
            raw=resp,
        )

    def fetch_inverted_sentinel(self, symbol: str) -> SmartMoneySignal:
        """Inverted scan: returns the OPPOSITE of detected smart-money direction.

        Use this to fade retail-dominated moves where smart money is absent.
        """
        signal = self.fetch_signal(symbol)
        inverted_direction = {
            "long": "short",
            "short": "long",
            "neutral": "neutral",
        }[signal.direction]
        return SmartMoneySignal(
            symbol=signal.symbol,
            direction=inverted_direction,
            confidence=signal.confidence,
            net_flow_usd=-signal.net_flow_usd,
            funding_divergence=signal.funding_divergence,
            large_print_detected=signal.large_print_detected,
            raw=signal.raw,
        )
