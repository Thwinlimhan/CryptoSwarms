from __future__ import annotations

import json

from cryptoswarms.crypto_strategy_pack import (
    cross_sectional_momentum_rotation,
    pairs_spread_mean_reversion,
    volatility_compression_breakout,
)


def _demo_pairs() -> dict[str, object]:
    base = [100.0 + i * 0.1 for i in range(120)]
    a = base[:-1] + [base[-1] * 1.05]
    b = base
    points = pairs_spread_mean_reversion(a, b, window=50, entry_z=2.0, exit_z=0.5)
    last = points[-1] if points else None
    return {
        "points": len(points),
        "latest": {
            "index": last.index,
            "zscore": last.zscore,
            "signal": last.signal,
            "action": last.action,
        }
        if last
        else None,
    }


def _demo_compression() -> dict[str, object]:
    candles = []
    price = 100.0
    for i in range(240):
        close = price + (0.03 if i % 2 == 0 else -0.02)
        if i > 230:
            close += 1.5
        candles.append({"open": price, "high": close + 0.1, "low": close - 0.1, "close": close})
        price = close

    points = volatility_compression_breakout(candles)
    latest = points[-1] if points else None
    return {
        "points": len(points),
        "latest": {
            "index": latest.index,
            "compression_percentile": latest.compression_percentile,
            "compressed": latest.compressed,
            "breakout_direction": latest.breakout_direction,
            "signal": latest.signal,
        }
        if latest
        else None,
    }


def _demo_rotation() -> dict[str, object]:
    prices = {
        "BTCUSDT": [100 + i * 0.5 for i in range(100)],
        "ETHUSDT": [100 + i * 0.35 for i in range(100)],
        "SOLUSDT": [100 + i * 0.7 for i in range(100)],
        "XRPUSDT": [130 - i * 0.15 for i in range(100)],
        "DOGEUSDT": [90 - i * 0.05 for i in range(100)],
    }
    result = cross_sectional_momentum_rotation(prices, lookback=30, top_k=3, bottom_k=2)
    return {
        "longs": result.longs,
        "shorts": result.shorts,
    }


def main() -> None:
    payload = {
        "pairs_spread_mean_reversion": _demo_pairs(),
        "volatility_compression_breakout": _demo_compression(),
        "cross_sectional_momentum_rotation": _demo_rotation(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
