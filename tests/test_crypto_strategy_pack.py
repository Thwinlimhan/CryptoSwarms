from datetime import datetime, timedelta, timezone

from cryptoswarms.crypto_strategy_pack import (
    cross_sectional_momentum_rotation,
    pairs_spread_mean_reversion,
    volatility_compression_breakout,
)


def test_pairs_spread_mean_reversion_detects_extreme_divergence():
    base = [100.0 + i * 0.1 for i in range(90)]
    a = base[:-1] + [base[-1] * 1.06]
    b = base

    signals = pairs_spread_mean_reversion(a, b, window=40, entry_z=2.0, exit_z=0.5)

    assert signals
    assert signals[-1].signal == -1
    assert signals[-1].action == "short_spread"


def test_volatility_compression_breakout_flags_compressed_breakout():
    candles = []
    price = 100.0
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)

    for i in range(240):
        if i < 120:
            close = price + (0.4 if i % 2 == 0 else -0.35)
            high = close + 1.0
            low = close - 1.0
        elif i < 230:
            close = price + (0.03 if i % 2 == 0 else -0.02)
            high = close + 0.1
            low = close - 0.1
        else:
            close = price + 1.8
            high = close + 0.1
            low = close - 0.1

        candles.append(
            {
                "time": (now + timedelta(minutes=i)).isoformat(),
                "open": price,
                "high": high,
                "low": low,
                "close": close,
            }
        )
        price = close

    points = volatility_compression_breakout(
        candles,
        range_window=30,
        percentile_window=120,
        compression_threshold=0.25,
        breakout_lookback=20,
    )

    assert points
    assert any(p.signal == 1 and p.breakout_direction == "long" for p in points[-20:])


def test_cross_sectional_momentum_rotation_ranks_assets():
    prices = {
        "BTCUSDT": [100 + i * 0.5 for i in range(80)],
        "ETHUSDT": [100 + i * 0.3 for i in range(80)],
        "SOLUSDT": [100 + i * 0.8 for i in range(80)],
        "XRPUSDT": [120 - i * 0.2 for i in range(80)],
        "DOGEUSDT": [90 - i * 0.1 for i in range(80)],
    }

    result = cross_sectional_momentum_rotation(prices, lookback=30, top_k=2, bottom_k=2)

    assert len(result.longs) == 2
    assert result.longs[0][0] == "SOLUSDT"
    assert len(result.shorts) == 2
    assert result.shorts[0][1] <= result.shorts[1][1]
