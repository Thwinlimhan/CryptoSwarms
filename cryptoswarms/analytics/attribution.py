"""Performance Attribution — decomposes PnL into signal, timing, and sizing contributions.

Helps identify which components of the trading system contribute
the most to profits and losses.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.analytics.attribution")


@dataclass
class Trade:
    """Trade for attribution analysis."""
    trade_id: str
    symbol: str
    side: str            # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    size_usd: float
    entry_time: datetime
    exit_time: datetime
    signal_confidence: float = 0.5
    signal_type: str = "unknown"
    pnl_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttributionResult:
    """PnL decomposition into contributing factors."""
    trade_id: str
    total_pnl_usd: float
    signal_contribution: float  # Alpha from signal quality
    timing_contribution: float  # Alpha from entry/exit timing
    sizing_contribution: float  # Alpha from position sizing
    market_contribution: float  # PnL from overall market movement
    details: dict[str, Any]


class PerformanceAttributor:
    """Decomposes trade PnL into contributing factors.

    Attribution framework:
    - Signal: Did the signal correctly predict direction?
    - Timing: Did we enter/exit at good prices relative to the move?
    - Sizing: Did we size appropriately given the opportunity?
    - Market: How much came from general market beta?
    """

    def __init__(
        self,
        market_returns: dict[str, float] | None = None,
    ) -> None:
        self._market_returns = market_returns or {}
        self._attributions: list[AttributionResult] = []

    def set_market_return(self, symbol: str, daily_return: float) -> None:
        """Set the market's daily return for a symbol (for beta extraction)."""
        self._market_returns[symbol] = daily_return

    def attribute_pnl(self, trade: Trade) -> AttributionResult:
        """Attribute a trade's PnL to its contributing factors.

        Args:
            trade: The completed trade to analyze.

        Returns:
            AttributionResult with decomposed contributions.
        """
        total_pnl = trade.pnl_usd
        if total_pnl == 0:
            total_pnl = self._calculate_pnl(trade)

        # 1. Signal contribution: Was the direction correct?
        signal_alpha = self._calculate_signal_alpha(trade)

        # 2. Timing contribution: Entry/exit quality
        timing_alpha = self._calculate_timing_alpha(trade)

        # 3. Sizing contribution: Position sizing effectiveness
        sizing_alpha = self._calculate_sizing_alpha(trade)

        # 4. Market contribution: Beta component
        market_return = self._market_returns.get(trade.symbol, 0.0)
        market_contribution = market_return * trade.size_usd

        # Normalize contributions to sum to total PnL
        raw_total = signal_alpha + timing_alpha + sizing_alpha + market_contribution
        if raw_total != 0 and total_pnl != 0:
            scale = total_pnl / raw_total
        else:
            scale = 1.0

        result = AttributionResult(
            trade_id=trade.trade_id,
            total_pnl_usd=round(total_pnl, 4),
            signal_contribution=round(signal_alpha * scale, 4),
            timing_contribution=round(timing_alpha * scale, 4),
            sizing_contribution=round(sizing_alpha * scale, 4),
            market_contribution=round(market_contribution * scale, 4),
            details={
                "signal_type": trade.signal_type,
                "signal_confidence": trade.signal_confidence,
                "hold_duration_s": (trade.exit_time - trade.entry_time).total_seconds(),
                "size_usd": trade.size_usd,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
            },
        )

        self._attributions.append(result)
        return result

    def _calculate_pnl(self, trade: Trade) -> float:
        """Calculate raw PnL from trade data."""
        if trade.side == "LONG":
            return (trade.exit_price - trade.entry_price) / trade.entry_price * trade.size_usd
        else:
            return (trade.entry_price - trade.exit_price) / trade.entry_price * trade.size_usd

    def _calculate_signal_alpha(self, trade: Trade) -> float:
        """Calculate signal quality contribution.

        Based on whether the signal correctly predicted direction
        and the confidence level.
        """
        correct_direction = (
            (trade.side == "LONG" and trade.exit_price > trade.entry_price) or
            (trade.side == "SHORT" and trade.exit_price < trade.entry_price)
        )

        base_alpha = abs(self._calculate_pnl(trade)) * trade.signal_confidence
        return base_alpha if correct_direction else -base_alpha

    def _calculate_timing_alpha(self, trade: Trade) -> float:
        """Calculate timing contribution.

        Estimates the quality of entry/exit timing by comparing
        actual prices to theoretical optimal prices.
        """
        price_move = abs(trade.exit_price - trade.entry_price) / trade.entry_price
        hold_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600

        # Longer holds with smaller moves = worse timing
        # Short holds with big moves = good timing
        if hold_hours > 0:
            efficiency = price_move / (hold_hours * 0.01)  # Normalize
        else:
            efficiency = 1.0

        timing_factor = min(1.0, efficiency) * 0.3  # 30% weight max
        return self._calculate_pnl(trade) * timing_factor

    def _calculate_sizing_alpha(self, trade: Trade) -> float:
        """Calculate sizing contribution.

        Based on whether the position size was appropriate
        given the signal confidence.
        """
        # Higher confidence + larger size in winning trade = good sizing
        # High confidence + large size in losing trade = bad sizing
        pnl = self._calculate_pnl(trade)
        confidence_alignment = trade.signal_confidence

        sizing_factor = 0.2  # 20% weight for sizing
        return pnl * confidence_alignment * sizing_factor

    def get_aggregate_attribution(self) -> dict[str, float]:
        """Get aggregate attribution across all analyzed trades."""
        if not self._attributions:
            return {
                "total_pnl": 0.0,
                "signal_contribution": 0.0,
                "timing_contribution": 0.0,
                "sizing_contribution": 0.0,
                "market_contribution": 0.0,
            }

        return {
            "total_pnl": round(sum(a.total_pnl_usd for a in self._attributions), 2),
            "signal_contribution": round(
                sum(a.signal_contribution for a in self._attributions), 2
            ),
            "timing_contribution": round(
                sum(a.timing_contribution for a in self._attributions), 2
            ),
            "sizing_contribution": round(
                sum(a.sizing_contribution for a in self._attributions), 2
            ),
            "market_contribution": round(
                sum(a.market_contribution for a in self._attributions), 2
            ),
        }

    def get_attribution_by_signal_type(self) -> dict[str, dict[str, float]]:
        """Get attribution breakdown by signal type."""
        by_type: dict[str, list[AttributionResult]] = {}
        for a in self._attributions:
            st = a.details.get("signal_type", "unknown")
            by_type.setdefault(st, []).append(a)

        return {
            signal_type: {
                "trade_count": len(results),
                "total_pnl": round(sum(r.total_pnl_usd for r in results), 2),
                "avg_signal_contribution": round(
                    sum(r.signal_contribution for r in results) / len(results), 4
                ) if results else 0.0,
            }
            for signal_type, results in by_type.items()
        }
