# agents/scanner/microstructure_primitives.py
"""
Academically grounded microstructure primitives.
Sources: Cont et al. (2014), Kyle (1985), Xu et al. (2018)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.research.lob_connector import LOBSnapshot


@dataclass(frozen=True)
class MicrostructurePrimitives:
    ofi: float               # Order Flow Imbalance [-1, +1]
    liquidity_gravity: float # Depth center-of-mass (price units)
    book_fragility: float    # 1/depth at best bid/ask [0, ∞)
    net_tape_pressure: float # Buy tape % − 0.5 [-0.5, +0.5]
    ofi_persistence: float   # Rolling OFI same-sign streak [0, 1]
    mid_price: float


def compute_ofi(lob: LOBSnapshot) -> float:
    """
    Order Flow Imbalance from Cont, Kukanov, Stoikov (2014).
    Uses top-of-book bid/ask sizes.
    Range: [-1, +1]. Positive = buy pressure dominant.
    """
    if not lob.bids or not lob.asks:
        return 0.0
    bid_size = lob.bids[0][1]
    ask_size = lob.asks[0][1]
    total = bid_size + ask_size
    if total < 1e-10:
        return 0.0
    return (bid_size - ask_size) / total


def compute_multilevel_ofi(lob: LOBSnapshot, n_levels: int = 5) -> float:
    """
    Multi-Level OFI from Xu, Gould, Howison (2018).
    Combines OFI across N book levels via PCA-inspired weighting.
    Substantially better predictive power than top-of-book only.
    """
    level_ofis: list[float] = []
    for i in range(min(n_levels, len(lob.bids), len(lob.asks))):
        bid_sz = lob.bids[i][1]
        ask_sz = lob.asks[i][1]
        total = bid_sz + ask_sz
        level_ofis.append((bid_sz - ask_sz) / total if total > 1e-10 else 0.0)

    if not level_ofis:
        return 0.0
    # Decay weights: closer levels get higher weight
    weights = [1.0 / (i + 1) for i in range(len(level_ofis))]
    total_w = sum(weights)
    return sum(o * w for o, w in zip(level_ofis, weights)) / total_w


def compute_liquidity_gravity(lob: LOBSnapshot, n_levels: int = 10) -> float:
    """
    Depth-weighted center of mass of the order book.
    Negative value = gravity pulling price down (ask-heavy).
    Positive value = gravity pulling price up (bid-heavy).
    Normalized as deviation from mid-price.
    """
    if not lob.bids or not lob.asks:
        return 0.0
    mid = (lob.bids[0][0] + lob.asks[0][0]) / 2.0

    bid_levels = lob.bids[:n_levels]
    ask_levels = lob.asks[:n_levels]

    bid_gravity = sum(p * s for p, s in bid_levels)
    ask_gravity = sum(p * s for p, s in ask_levels)
    bid_depth = sum(s for _, s in bid_levels)
    ask_depth = sum(s for _, s in ask_levels)

    if bid_depth < 1e-10 or ask_depth < 1e-10:
        return 0.0

    bid_center = bid_gravity / bid_depth
    ask_center = ask_gravity / ask_depth
    # Positive = bid center of mass is closer to mid (bid support)
    # Negative = ask center of mass is closer to mid (ask pressure)
    if mid < 1e-10:
        return 0.0
    return ((mid - bid_center) - (ask_center - mid)) / mid


def compute_book_fragility(lob: LOBSnapshot) -> float:
    """
    Inverse of top-of-book depth. High = thin book = violent moves likely.
    Kyle (1985): depth = amount of flow to move price by one tick.
    Normalized by mid-price to be comparable across instruments.
    """
    if not lob.bids or not lob.asks:
        return 1.0
    mid = (lob.bids[0][0] + lob.asks[0][0]) / 2.0
    best_depth = lob.bids[0][1] + lob.asks[0][1]
    if best_depth < 1e-10 or mid < 1e-10:
        return 1.0
    # Scale: fragility = 1 / (depth_in_USD). Clip at [0, 1].
    depth_usd = best_depth * mid
    return min(1.0, 1000.0 / max(depth_usd, 1.0))  # 1000 USD is "thin"


def compute_net_tape_pressure(trades: list[dict], lookback_n: int = 50) -> float:
    """
    Net buying pressure from recent trade tape.
    Returns fraction of buy-initiated volume minus 0.5.
    Range: [-0.5, +0.5]. Positive = buy pressure.
    """
    recent = trades[-lookback_n:]
    if not recent:
        return 0.0
    buy_vol = sum(float(t.get("sz", 0)) for t in recent if str(t.get("side", "")).lower() == "b")
    total_vol = sum(float(t.get("sz", 0)) for t in recent)
    if total_vol < 1e-10:
        return 0.0
    return (buy_vol / total_vol) - 0.5


def compute_primitives(
    lob: LOBSnapshot,
    trades: list[dict],
    ofi_history: list[float],  # last N OFI values for persistence
    n_levels: int = 5,
    persistence_window: int = 10,
) -> MicrostructurePrimitives:
    ofi = compute_multilevel_ofi(lob, n_levels)
    gravity = compute_liquidity_gravity(lob, n_levels * 2)
    fragility = compute_book_fragility(lob)
    tape = compute_net_tape_pressure(trades)

    # OFI persistence: fraction of last N readings with same sign as current
    if ofi_history:
        sign_match = sum(
            1 for h in ofi_history[-persistence_window:]
            if (h > 0) == (ofi > 0)
        )
        persistence = sign_match / min(len(ofi_history), persistence_window)
    else:
        persistence = 0.5

    mid = (lob.bids[0][0] + lob.asks[0][0]) / 2.0 if lob.bids and lob.asks else 0.0

    return MicrostructurePrimitives(
        ofi=round(ofi, 4),
        liquidity_gravity=round(gravity, 6),
        book_fragility=round(fragility, 4),
        net_tape_pressure=round(tape, 4),
        ofi_persistence=round(persistence, 4),
        mid_price=round(mid, 2),
    )
