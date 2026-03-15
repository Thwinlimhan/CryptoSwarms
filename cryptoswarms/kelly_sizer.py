"""Kelly Criterion position sizer.

Sizes positions proportional to edge quality, not fixed amounts.
Uses fractional Kelly (default 25%) for safety.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KellyResult:
    full_kelly_fraction: float
    fractional_kelly: float
    suggested_size_usd: float
    edge_quality: str           # "strong", "moderate", "weak", "no_edge"
    max_allowed_usd: float


def kelly_size(
    *,
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    bankroll_usd: float,
    kelly_fraction: float = 0.25,    # Use 25% Kelly for safety
    max_position_pct: float = 0.10,  # Never risk more than 10% of bankroll
    min_position_usd: float = 10.0,  # Minimum trade size
) -> KellyResult:
    """Calculate optimal position size using Kelly Criterion.
    
    Full Kelly: f* = (bp - q) / b
    where:
        b = avg_win / avg_loss (win/loss ratio)
        p = probability of winning
        q = 1 - p
    
    We use fractional Kelly (typically 25-50%) because:
    - Full Kelly has massive variance
    - Our win rate estimates are imprecise
    - Crypto is fat-tailed (extreme moves happen more than expected)
    """
    p = max(0.001, min(0.999, win_rate))
    q = 1.0 - p

    avg_win = abs(avg_win_pct)
    avg_loss = abs(avg_loss_pct)

    if avg_loss <= 0:
        return KellyResult(0.0, 0.0, 0.0, "no_edge", 0.0)

    b = avg_win / avg_loss  # Win/loss ratio

    # Kelly formula
    full_kelly = (b * p - q) / b

    # Classify edge quality
    if full_kelly <= 0:
        edge_quality = "no_edge"
    elif full_kelly < 0.05:
        edge_quality = "weak"
    elif full_kelly < 0.15:
        edge_quality = "moderate"
    else:
        edge_quality = "strong"

    # Apply fractional Kelly
    frac_kelly = max(0.0, full_kelly * kelly_fraction)

    # Cap at max position percentage
    capped = min(frac_kelly, max_position_pct)

    # Calculate USD size
    max_allowed = bankroll_usd * max_position_pct
    suggested = max(0.0, bankroll_usd * capped)
    suggested = min(suggested, max_allowed)

    # Floor at minimum
    if 0 < suggested < min_position_usd:
        suggested = 0.0  # Too small to trade

    return KellyResult(
        full_kelly_fraction=round(full_kelly, 6),
        fractional_kelly=round(frac_kelly, 6),
        suggested_size_usd=round(suggested, 2),
        edge_quality=edge_quality,
        max_allowed_usd=round(max_allowed, 2),
    )


def kelly_from_trades(
    *,
    wins: int,
    losses: int,
    gross_profit: float,
    gross_loss: float,
    bankroll_usd: float,
    kelly_fraction: float = 0.25,
) -> KellyResult:
    """Convenience: compute Kelly from raw trade statistics."""
    total = wins + losses
    if total < 10:
        # Not enough data — use minimum sizing
        return KellyResult(0.0, 0.0, bankroll_usd * 0.01, "weak", bankroll_usd * 0.10)

    win_rate = wins / total
    avg_win_pct = (gross_profit / wins / bankroll_usd) if wins > 0 else 0.0
    avg_loss_pct = (gross_loss / losses / bankroll_usd) if losses > 0 else 0.0

    return kelly_size(
        win_rate=win_rate,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        bankroll_usd=bankroll_usd,
        kelly_fraction=kelly_fraction,
    )
