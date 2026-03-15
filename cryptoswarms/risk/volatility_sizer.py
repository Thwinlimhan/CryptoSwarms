"""Volatility-Adjusted Position Sizer — scales position sizes based on realized volatility.

Reduces position sizes in high-volatility markets and increases them
in low-volatility markets to target a consistent level of risk.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("swarm.risk.volatility_sizer")


@dataclass(frozen=True)
class SizingResult:
    """Result of volatility-adjusted sizing calculation."""
    original_size_usd: float
    adjusted_size_usd: float
    adjustment_factor: float
    realized_volatility: float
    target_volatility: float
    message: str


class VolatilityAdjustedSizer:
    """Adjusts position sizes based on realized volatility.

    Targets a constant level of risk by scaling positions inversely
    with volatility. High vol → smaller positions, low vol → larger.
    """

    def __init__(
        self,
        target_volatility: float = 0.02,  # 2% daily target
        max_vol_adjustment: float = 2.0,  # Max 2x size increase
        min_vol_adjustment: float = 0.2,  # Minimum 20% of base size
        lookback_days: int = 30,
    ) -> None:
        self.target_volatility = target_volatility
        self.max_vol_adjustment = max_vol_adjustment
        self.min_vol_adjustment = min_vol_adjustment
        self.lookback_days = lookback_days
        self._volatility_cache: dict[str, float] = {}

    @staticmethod
    def calculate_realized_volatility(
        returns: list[float],
        annualize: bool = False,
    ) -> float:
        """Calculate realized volatility from a series of returns.

        Args:
            returns: List of daily returns (as decimals, e.g., 0.02 for 2%).
            annualize: If True, annualize the daily volatility.

        Returns:
            Realized volatility as a decimal.
        """
        if len(returns) < 2:
            return 0.0

        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
        daily_vol = math.sqrt(variance)

        if annualize:
            return daily_vol * math.sqrt(365)
        return daily_vol

    def set_volatility(self, symbol: str, volatility: float) -> None:
        """Manually set volatility for a symbol (e.g., from an external source)."""
        self._volatility_cache[symbol] = volatility

    def _get_realized_volatility(
        self,
        symbol: str,
        returns: list[float] | None = None,
    ) -> float:
        """Get realized volatility for a symbol."""
        if returns:
            vol = self.calculate_realized_volatility(returns)
            self._volatility_cache[symbol] = vol
            return vol

        # Use cached value
        return self._volatility_cache.get(symbol, self.target_volatility)

    def calculate_position_size(
        self,
        symbol: str,
        base_size: float,
        returns: list[float] | None = None,
    ) -> SizingResult:
        """Calculate volatility-adjusted position size.

        Args:
            symbol: Trading pair.
            base_size: Base position size in USD.
            returns: Optional list of recent returns for vol calculation.

        Returns:
            SizingResult with the adjusted position size.
        """
        volatility = self._get_realized_volatility(symbol, returns)

        if volatility <= 0:
            logger.warning("Zero volatility for %s, using base size", symbol)
            return SizingResult(
                original_size_usd=base_size,
                adjusted_size_usd=base_size,
                adjustment_factor=1.0,
                realized_volatility=0.0,
                target_volatility=self.target_volatility,
                message="Zero volatility, no adjustment",
            )

        # Calculate adjustment factor
        vol_adjustment = self.target_volatility / volatility
        clamped_adjustment = max(
            self.min_vol_adjustment,
            min(vol_adjustment, self.max_vol_adjustment),
        )

        adjusted_size = base_size * clamped_adjustment

        logger.debug(
            "Vol sizing %s: vol=%.4f, target=%.4f, adj=%.2f, "
            "base=$%.2f → $%.2f",
            symbol, volatility, self.target_volatility,
            clamped_adjustment, base_size, adjusted_size,
        )

        was_clamped = clamped_adjustment != vol_adjustment
        message = (
            f"Adjusted by {clamped_adjustment:.2f}x"
            f"{' (clamped)' if was_clamped else ''}"
        )

        return SizingResult(
            original_size_usd=round(base_size, 2),
            adjusted_size_usd=round(adjusted_size, 2),
            adjustment_factor=round(clamped_adjustment, 4),
            realized_volatility=round(volatility, 6),
            target_volatility=self.target_volatility,
            message=message,
        )
