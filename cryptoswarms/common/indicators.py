"""Technical Indicators for CryptoSwarms.

Pure Python implementations of common indicators for use in backtesting and scanning.
"""
from __future__ import annotations
import statistics

def calculate_rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100.0
    
    # RS = avg_gain / avg_loss
    # For subsequent periods, use Wilder's Smoothing
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_ema(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period # Start with SMA
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_macd(prices: list[float]) -> dict[str, float] | None:
    if len(prices) < 26:
        return None
    
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    
    if ema12 is None or ema26 is None:
        return None
        
    macd_line = ema12 - ema26
    
    # We'd need a history of MACD lines to calculate the Signal line properly
    # For a one-off backtest step, we assume this is called with enough history
    return {"macd": macd_line}

def calculate_bollinger_bands(prices: list[float], period: int, std_dev: float) -> dict[str, float] | None:
    if len(prices) < period:
        return None
    
    mean = statistics.mean(prices[-period:])
    stdev = statistics.pstdev(prices[-period:])
    
    return {
        "middle": mean,
        "upper": mean + (std_dev * stdev),
        "lower": mean - (std_dev * stdev)
    }

def calculate_vwap(candles: list[list[Any]]) -> float:
    """Calculates VWAP from a list of candles [time, open, high, low, close, volume]."""
    total_pv = 0.0
    total_v = 0.0
    for c in candles:
        price = (float(c[2]) + float(c[3]) + float(c[4])) / 3 # Typical price
        vol = float(c[5])
        total_pv += price * vol
        total_v += vol
    return total_pv / total_v if total_v > 0 else 0.0
