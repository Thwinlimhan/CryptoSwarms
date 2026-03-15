"""Sector Risk Manager — enforces sector concentration limits.

Prevents overexposure to any single crypto sector by tracking
and limiting exposure by sector category.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.risk.sector_limits")


# Default sector classification for crypto assets
DEFAULT_SECTOR_MAP: dict[str, str] = {
    # Layer 1
    "BTCUSDT": "store_of_value",
    "ETHUSDT": "smart_contracts",
    "SOLUSDT": "smart_contracts",
    "AVAXUSDT": "smart_contracts",
    "DOTUSDT": "smart_contracts",
    "ATOMUSDT": "smart_contracts",
    "NEARUSDT": "smart_contracts",
    "ADAUSDT": "smart_contracts",
    # Layer 2
    "MATICUSDT": "layer2",
    "ARBUSDT": "layer2",
    "OPUSDT": "layer2",
    # DeFi
    "UNIUSDT": "defi",
    "AAVEUSDT": "defi",
    "MKRUSDT": "defi",
    "COMPUSDT": "defi",
    "SUSHIUSDT": "defi",
    "CRVUSDT": "defi",
    # Exchange tokens
    "BNBUSDT": "exchange",
    # Meme
    "DOGEUSDT": "meme",
    "SHIBUSDT": "meme",
    "PEPEUSDT": "meme",
    # AI
    "FETUSDT": "ai",
    "AGIXUSDT": "ai",
    "OCEANUSDT": "ai",
    "RENDERUSDT": "ai",
    # Gaming
    "AXSUSDT": "gaming",
    "SANDUSDT": "gaming",
    "MANAUSDT": "gaming",
}

# Default sector exposure limits (as percentage of total portfolio)
DEFAULT_SECTOR_LIMITS: dict[str, float] = {
    "store_of_value": 0.40,  # 40% max in BTC
    "smart_contracts": 0.35,  # 35% max
    "layer2": 0.20,
    "defi": 0.25,
    "exchange": 0.10,
    "meme": 0.10,  # Very limited meme exposure
    "ai": 0.15,
    "gaming": 0.15,
    "unknown": 0.15,  # Unclassified assets
}


@dataclass(frozen=True)
class SectorCheckResult:
    """Result of a sector limit check."""
    allowed: bool
    sector: str
    current_exposure: float
    proposed_exposure: float
    sector_limit: float
    message: str


class SectorRiskManager:
    """Enforces sector concentration limits in the portfolio.

    Tracks exposure by sector and prevents adding positions
    that would exceed sector limits.
    """

    def __init__(
        self,
        sector_map: dict[str, str] | None = None,
        sector_limits: dict[str, float] | None = None,
        total_portfolio_usd: float = 10_000.0,
    ) -> None:
        self._sector_map = sector_map or DEFAULT_SECTOR_MAP
        self.sector_limits = sector_limits or DEFAULT_SECTOR_LIMITS
        self.total_portfolio_usd = total_portfolio_usd
        self._current_exposure: dict[str, float] = {}

    def _get_symbol_sector(self, symbol: str) -> str:
        """Get the sector for a given symbol."""
        return self._sector_map.get(symbol.upper(), "unknown")

    def _get_sector_exposure(self, sector: str) -> float:
        """Get current USD exposure for a sector."""
        return self._current_exposure.get(sector, 0.0)

    def update_exposure(self, positions: list[dict[str, Any]]) -> None:
        """Update sector exposures from current positions.

        Args:
            positions: List of position dicts with 'symbol' and 'size_usd' keys.
        """
        self._current_exposure = {}
        for pos in positions:
            symbol = pos.get("symbol", "")
            size_usd = pos.get("size_usd", 0.0)
            sector = self._get_symbol_sector(symbol)
            self._current_exposure[sector] = (
                self._current_exposure.get(sector, 0.0) + size_usd
            )

    def check_sector_limits(
        self,
        symbol: str,
        size_usd: float,
    ) -> SectorCheckResult:
        """Check if adding a position would exceed sector limits.

        Args:
            symbol: Trading pair.
            size_usd: Proposed position size in USD.

        Returns:
            SectorCheckResult with the decision.
        """
        sector = self._get_symbol_sector(symbol)
        current_exposure = self._get_sector_exposure(sector)
        proposed_exposure = current_exposure + size_usd
        limit = self.sector_limits.get(sector, self.sector_limits.get("unknown", 0.15))
        limit_usd = self.total_portfolio_usd * limit

        allowed = proposed_exposure <= limit_usd

        if not allowed:
            logger.warning(
                "Sector limit breached for %s (%s): $%.2f + $%.2f = $%.2f > $%.2f (%.0f%%)",
                symbol, sector, current_exposure, size_usd,
                proposed_exposure, limit_usd, limit * 100,
            )

        return SectorCheckResult(
            allowed=allowed,
            sector=sector,
            current_exposure=round(current_exposure, 2),
            proposed_exposure=round(proposed_exposure, 2),
            sector_limit=round(limit_usd, 2),
            message=(
                f"Allowed: {sector} exposure ${proposed_exposure:.2f} / ${limit_usd:.2f}"
                if allowed
                else f"Blocked: {sector} exposure would exceed limit "
                     f"(${proposed_exposure:.2f} > ${limit_usd:.2f})"
            ),
        )

    def get_sector_breakdown(self) -> dict[str, dict[str, Any]]:
        """Get current exposure breakdown by sector."""
        result: dict[str, dict[str, Any]] = {}
        for sector in set(list(self._current_exposure.keys()) + list(self.sector_limits.keys())):
            exposure = self._current_exposure.get(sector, 0.0)
            limit = self.sector_limits.get(sector, 0.15)
            limit_usd = self.total_portfolio_usd * limit
            result[sector] = {
                "exposure_usd": round(exposure, 2),
                "limit_usd": round(limit_usd, 2),
                "utilization_pct": round(exposure / limit_usd * 100, 1) if limit_usd > 0 else 0,
            }
        return result
