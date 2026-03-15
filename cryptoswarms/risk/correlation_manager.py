"""Correlation Risk Manager — prevents correlated position concentration.

Checks that adding a new position doesn't create excessive
correlation risk in the portfolio.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.risk.correlation")


# Pre-defined correlation groups for crypto assets
DEFAULT_CORRELATION_GROUPS: dict[str, list[str]] = {
    "btc_ecosystem": ["BTCUSDT", "BTCUSD", "WBTCUSDT"],
    "eth_ecosystem": ["ETHUSDT", "ETHUSD", "STETHUSDT"],
    "defi": ["UNIUSDT", "AAVEUSDT", "MKRUSDT", "COMPUSDT", "SUSHIUSDT"],
    "layer1": ["SOLUSDT", "AVAXUSDT", "DOTUSDT", "ATOMUSDT", "NEARUSDT"],
    "layer2": ["MATICUSDT", "ARBUSDT", "OPUSDT"],
    "meme": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT"],
    "exchange_tokens": ["BNBUSDT", "FTMUSDT"],
    "ai_tokens": ["FETUSDT", "AGIXUSDT", "OCEANUSDT", "RENDERUSDT"],
}

# Default pair-level approximate correlations (simplified)
DEFAULT_PAIR_CORRELATIONS: dict[tuple[str, str], float] = {
    ("BTCUSDT", "ETHUSDT"): 0.85,
    ("BTCUSDT", "SOLUSDT"): 0.75,
    ("BTCUSDT", "BNBUSDT"): 0.80,
    ("ETHUSDT", "SOLUSDT"): 0.70,
    ("ETHUSDT", "MATICUSDT"): 0.75,
}


@dataclass(frozen=True)
class CorrelationCheckResult:
    """Result of a correlation risk check."""
    allowed: bool
    portfolio_correlation_risk: float
    max_allowed: float
    correlated_positions: list[str]
    message: str


class CorrelationRiskManager:
    """Manages correlation risk across the portfolio.

    Prevents excessive exposure to correlated assets by checking
    new positions against existing positions.
    """

    def __init__(
        self,
        max_correlation_risk: float = 0.7,
        max_same_group_positions: int = 3,
        correlation_groups: dict[str, list[str]] | None = None,
        pair_correlations: dict[tuple[str, str], float] | None = None,
    ) -> None:
        self.max_correlation_risk = max_correlation_risk
        self.max_same_group_positions = max_same_group_positions
        self._groups = correlation_groups or DEFAULT_CORRELATION_GROUPS
        self._pair_correlations = pair_correlations or DEFAULT_PAIR_CORRELATIONS

    def _get_symbol_group(self, symbol: str) -> str | None:
        """Find which correlation group a symbol belongs to."""
        for group_name, symbols in self._groups.items():
            if symbol.upper() in [s.upper() for s in symbols]:
                return group_name
        return None

    def _get_pair_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Get the estimated correlation between two symbols."""
        # Check direct pair
        key = (symbol_a.upper(), symbol_b.upper())
        rev_key = (symbol_b.upper(), symbol_a.upper())

        if key in self._pair_correlations:
            return self._pair_correlations[key]
        if rev_key in self._pair_correlations:
            return self._pair_correlations[rev_key]

        # Check if in same group
        group_a = self._get_symbol_group(symbol_a)
        group_b = self._get_symbol_group(symbol_b)

        if group_a and group_b and group_a == group_b:
            return 0.8  # High correlation within same group

        # Default moderate crypto correlation
        return 0.4

    def _calculate_portfolio_correlation(
        self, positions: list[str]
    ) -> float:
        """Calculate aggregate portfolio correlation risk.

        Uses average pairwise correlation as a measure of concentration risk.
        """
        if len(positions) <= 1:
            return 0.0

        total_correlation = 0.0
        pair_count = 0

        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                total_correlation += self._get_pair_correlation(
                    positions[i], positions[j]
                )
                pair_count += 1

        return total_correlation / pair_count if pair_count > 0 else 0.0

    def check_correlation_limits(
        self,
        new_symbol: str,
        existing_positions: list[str],
    ) -> CorrelationCheckResult:
        """Check if adding a new symbol would breach correlation limits.

        Args:
            new_symbol: The symbol to potentially add.
            existing_positions: List of currently held symbols.

        Returns:
            CorrelationCheckResult with the decision.
        """
        if not existing_positions:
            return CorrelationCheckResult(
                allowed=True,
                portfolio_correlation_risk=0.0,
                max_allowed=self.max_correlation_risk,
                correlated_positions=[],
                message="No existing positions, allowed",
            )

        # Check same-group concentration
        new_group = self._get_symbol_group(new_symbol)
        if new_group:
            same_group = [
                p for p in existing_positions
                if self._get_symbol_group(p) == new_group
            ]
            if len(same_group) >= self.max_same_group_positions:
                return CorrelationCheckResult(
                    allowed=False,
                    portfolio_correlation_risk=1.0,
                    max_allowed=self.max_correlation_risk,
                    correlated_positions=same_group,
                    message=(
                        f"Too many positions in group '{new_group}': "
                        f"{len(same_group)} >= {self.max_same_group_positions}"
                    ),
                )

        # Check portfolio-level correlation
        all_positions = existing_positions + [new_symbol]
        total_correlation_risk = self._calculate_portfolio_correlation(all_positions)

        # Find highly correlated existing positions
        correlated = [
            p for p in existing_positions
            if self._get_pair_correlation(new_symbol, p) > 0.6
        ]

        allowed = total_correlation_risk < self.max_correlation_risk

        if not allowed:
            logger.warning(
                "Correlation limit breached for %s: risk=%.2f > max=%.2f, "
                "correlated_with=%s",
                new_symbol, total_correlation_risk, self.max_correlation_risk,
                correlated,
            )

        return CorrelationCheckResult(
            allowed=allowed,
            portfolio_correlation_risk=round(total_correlation_risk, 4),
            max_allowed=self.max_correlation_risk,
            correlated_positions=correlated,
            message=(
                f"Allowed" if allowed
                else f"Correlation risk {total_correlation_risk:.2f} exceeds limit"
            ),
        )
