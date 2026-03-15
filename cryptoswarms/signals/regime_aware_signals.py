"""Regime-Aware Signal Generator — generates signals appropriate to the current market regime.

Produces different signal types based on detected market conditions
(trending, high-volatility, ranging) to improve signal quality.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("swarm.signals.regime")


class MarketRegime(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RANGING = "ranging"
    UNKNOWN = "unknown"


@dataclass
class Signal:
    """A trading signal with confidence and metadata."""
    symbol: str
    signal_type: str  # "momentum", "volatility_breakout", "mean_reversion", etc.
    direction: str  # "BUY", "SELL", or "NEUTRAL"
    confidence: float  # 0.0 to 1.0
    regime: MarketRegime
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.direction in ("BUY", "SELL") and self.confidence > 0.0


class RegimeAwareSignalGenerator:
    """Generates signals appropriate to detected market regimes.

    Different market conditions require different signal strategies:
    - Trending: momentum/trend-following signals
    - High volatility: breakout signals
    - Ranging: no signals (avoid whipsaws)
    - Low volatility: mean reversion signals
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        regime_thresholds: dict[str, float] | None = None,
    ) -> None:
        self.min_confidence = min_confidence
        self.regime_thresholds = regime_thresholds or {
            "trend_strength": 0.3,
            "volatility_high": 2.0,   # ATR multiplier threshold
            "volatility_low": 0.5,
        }

    def generate_signal(
        self,
        symbol: str,
        regime: str | MarketRegime,
        market_data: dict[str, Any] | None = None,
    ) -> Signal | None:
        """Generate a signal appropriate for the current market regime.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT").
            regime: Current detected market regime.
            market_data: Optional market data for signal calculation.

        Returns:
            Signal if conditions are met, None otherwise.
        """
        if isinstance(regime, str):
            try:
                regime = MarketRegime(regime)
            except ValueError:
                regime = MarketRegime.UNKNOWN

        data = market_data or {}

        if regime == MarketRegime.HIGH_VOLATILITY:
            return self._volatility_breakout_signal(symbol, data, regime)
        elif regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            return self._momentum_signal(symbol, data, regime)
        elif regime == MarketRegime.LOW_VOLATILITY:
            return self._mean_reversion_signal(symbol, data, regime)
        elif regime == MarketRegime.RANGING:
            # No signals in ranging markets to avoid whipsaws
            logger.debug("No signal for %s: ranging market", symbol)
            return None
        else:
            logger.debug("No signal for %s: unknown regime", symbol)
            return None

    def _volatility_breakout_signal(
        self, symbol: str, data: dict[str, Any], regime: MarketRegime,
    ) -> Signal:
        """Generate a breakout signal during high volatility."""
        # Determine direction from price vs recent range
        price = data.get("price", 0)
        upper_band = data.get("upper_band", 0)
        lower_band = data.get("lower_band", 0)

        if price > upper_band and upper_band > 0:
            direction = "BUY"
            confidence = min(0.8, 0.5 + (price - upper_band) / upper_band * 10)
        elif price < lower_band and lower_band > 0:
            direction = "SELL"
            confidence = min(0.8, 0.5 + (lower_band - price) / lower_band * 10)
        else:
            direction = "NEUTRAL"
            confidence = 0.0

        return Signal(
            symbol=symbol,
            signal_type="volatility_breakout",
            direction=direction,
            confidence=max(0.0, confidence),
            regime=regime,
            metadata={"price": price, "upper_band": upper_band, "lower_band": lower_band},
        )

    def _momentum_signal(
        self, symbol: str, data: dict[str, Any], regime: MarketRegime,
    ) -> Signal:
        """Generate a momentum/trend-following signal."""
        trend_strength = data.get("trend_strength", 0.0)
        direction = "BUY" if regime == MarketRegime.TRENDING_UP else "SELL"
        confidence = min(0.9, abs(trend_strength))

        if confidence < self.min_confidence:
            direction = "NEUTRAL"
            confidence = 0.0

        return Signal(
            symbol=symbol,
            signal_type="momentum",
            direction=direction,
            confidence=confidence,
            regime=regime,
            metadata={"trend_strength": trend_strength},
        )

    def _mean_reversion_signal(
        self, symbol: str, data: dict[str, Any], regime: MarketRegime,
    ) -> Signal:
        """Generate a mean reversion signal during low volatility."""
        z_score = data.get("z_score", 0.0)

        if z_score > 2.0:
            direction = "SELL"
            confidence = min(0.7, abs(z_score) / 4.0)
        elif z_score < -2.0:
            direction = "BUY"
            confidence = min(0.7, abs(z_score) / 4.0)
        else:
            direction = "NEUTRAL"
            confidence = 0.0

        return Signal(
            symbol=symbol,
            signal_type="mean_reversion",
            direction=direction,
            confidence=confidence,
            regime=regime,
            metadata={"z_score": z_score},
        )
