from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean, pstdev


@dataclass(frozen=True)
class PairSpreadPoint:
    index: int
    zscore: float
    signal: int
    action: str


@dataclass(frozen=True)
class CompressionBreakoutPoint:
    index: int
    compression_percentile: float
    compressed: bool
    breakout_direction: str
    signal: int


@dataclass(frozen=True)
class MomentumRotationResult:
    ranked: list[tuple[str, float]]
    longs: list[tuple[str, float]]
    shorts: list[tuple[str, float]]


def pairs_spread_mean_reversion(
    prices_a: list[float],
    prices_b: list[float],
    *,
    window: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> list[PairSpreadPoint]:
    if len(prices_a) != len(prices_b):
        raise ValueError("prices_a and prices_b must have the same length")
    if len(prices_a) < window:
        return []

    spread: list[float] = []
    for a, b in zip(prices_a, prices_b):
        if a <= 0 or b <= 0:
            raise ValueError("prices must be positive for log spread")
        spread.append(math.log(a) - math.log(b))

    out: list[PairSpreadPoint] = []
    for i in range(window - 1, len(spread)):
        hist = spread[i - window + 1 : i + 1]
        mu = fmean(hist)
        sigma = pstdev(hist)
        z = 0.0 if sigma == 0 else (spread[i] - mu) / sigma

        if z > entry_z:
            signal = -1
            action = "short_spread"
        elif z < -entry_z:
            signal = 1
            action = "long_spread"
        elif abs(z) < exit_z:
            signal = 0
            action = "exit_or_flat"
        else:
            signal = 0
            action = "hold"

        out.append(PairSpreadPoint(index=i, zscore=round(z, 6), signal=signal, action=action))
    return out


def volatility_compression_breakout(
    candles: list[dict[str, float]],
    *,
    range_window: int = 30,
    percentile_window: int = 180,
    compression_threshold: float = 0.2,
    breakout_lookback: int = 20,
) -> list[CompressionBreakoutPoint]:
    if not candles:
        return []

    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    ranges = [max(0.0, h - l) for h, l in zip(highs, lows)]

    out: list[CompressionBreakoutPoint] = []
    compressed_by_index: dict[int, bool] = {}
    for i in range(len(candles)):
        if i + 1 < range_window or i + 1 < breakout_lookback:
            continue

        avg_range_series: list[float] = []
        start = max(range_window - 1, i - percentile_window + 1)
        for j in range(start, i + 1):
            segment = ranges[j - range_window + 1 : j + 1]
            avg_range_series.append(fmean(segment))

        current_avg_range = avg_range_series[-1]
        less_equal = sum(1 for x in avg_range_series if x <= current_avg_range)
        percentile = less_equal / len(avg_range_series)

        # Use quantile threshold for compression classification so prolonged low-volatility
        # regimes remain flagged as compressed instead of drifting to median percentile.
        ordered = sorted(avg_range_series)
        q_index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * compression_threshold)))
        quantile_cut = ordered[q_index]
        compressed = current_avg_range <= quantile_cut
        compressed_by_index[i] = compressed

        prev_high = max(highs[i - breakout_lookback + 1 : i]) if breakout_lookback > 1 else highs[i - 1]
        prev_low = min(lows[i - breakout_lookback + 1 : i]) if breakout_lookback > 1 else lows[i - 1]

        if closes[i] > prev_high:
            direction = "long"
        elif closes[i] < prev_low:
            direction = "short"
        else:
            direction = "none"

        # Allow breakout signal if compression happened recently, not only same-bar.
        compression_context = compressed or compressed_by_index.get(i - 1, False) or compressed_by_index.get(i - 2, False)

        if direction == "long" and compression_context:
            signal = 1
        elif direction == "short" and compression_context:
            signal = -1
        else:
            signal = 0

        out.append(
            CompressionBreakoutPoint(
                index=i,
                compression_percentile=round(percentile, 6),
                compressed=compressed,
                breakout_direction=direction,
                signal=signal,
            )
        )

    return out


def cross_sectional_momentum_rotation(
    prices_by_symbol: dict[str, list[float]],
    *,
    lookback: int = 63,
    top_k: int = 3,
    bottom_k: int = 3,
) -> MomentumRotationResult:
    scores: list[tuple[str, float]] = []

    for symbol, series in prices_by_symbol.items():
        if len(series) <= lookback:
            continue
        latest = float(series[-1])
        prior = float(series[-1 - lookback])
        if latest <= 0 or prior <= 0:
            continue
        momentum = (latest / prior) - 1.0
        scores.append((symbol, momentum))

    ranked = sorted(scores, key=lambda x: x[1], reverse=True)
    longs = ranked[: max(0, top_k)]
    shorts = list(reversed(ranked[-max(0, bottom_k) :])) if ranked else []
    return MomentumRotationResult(ranked=ranked, longs=longs, shorts=shorts)

