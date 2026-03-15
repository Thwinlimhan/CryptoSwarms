"""Async Binance public-API market data — with rate limiting and response caching.

No API keys required — all endpoints are public:
  - GET /api/v3/ticker/24hr   → top symbols by volume (cached 30s)
  - GET /api/v3/klines         → OHLCV candles for breakout detection
  - GET /fapi/v1/premiumIndex  → perp funding rates
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"

# Only trade USDT-margined pairs on Binance
_QUOTE_ASSET = "USDT"

# Rate limiter: max concurrent outbound requests
_RATE_LIMITER = asyncio.Semaphore(10)

# Simple TTL cache for the expensive all-ticker endpoint
_TICKER_CACHE: dict[str, Any] = {}
_TICKER_CACHE_TS: float = 0.0
_TICKER_CACHE_TTL: float = 30.0  # seconds


@dataclass
class BinanceMarketData:
    """Async Binance public-API market-data source.

    Implements the same conceptual interface as ``MarketDataSource``
    but is async-native.  The agent runner calls the ``async`` methods.
    """

    session: httpx.AsyncClient | None = field(default=None, repr=False)
    _symbol_cache: list[str] = field(default_factory=list, repr=False)
    _funding_cache: dict[str, float] = field(default_factory=dict, repr=False)
    _kline_cache: dict[str, list[list[Any]]] = field(default_factory=dict, repr=False)

    # ── helpers ──────────────────────────────────────────────────
    async def _get(self, url: str, params: dict | None = None, retries: int = 3) -> Any:
        """GET with rate limiting, retry, and exponential back-off."""
        async with _RATE_LIMITER:
            if self.session is None or self.session.is_closed:
                self.session = httpx.AsyncClient(timeout=15.0)
            for attempt in range(retries):
                try:
                    resp = await self.session.get(url, params=params)
                    resp.raise_for_status()
                    return resp.json()
                except Exception as exc:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    if attempt < retries - 1:
                        logger.warning(
                            "Binance request failed (attempt %d/%d): %s %s → %s (retry in %ds)",
                            attempt + 1, retries, url, params, exc, wait,
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.warning(
                            "Binance request failed after %d attempts: %s %s → %s",
                            retries, url, params, exc,
                        )
                        return None

    async def close(self) -> None:
        if self.session and not self.session.is_closed:
            await self.session.aclose()

    # ── cached ticker fetch ──────────────────────────────────────
    async def _get_all_tickers(self) -> list[dict[str, Any]]:
        """Return all 24h tickers — cached for _TICKER_CACHE_TTL seconds.

        The Binance ticker endpoint returns ~2000 symbols and is expensive.
        Caching avoids hammering it on every scan cycle.
        """
        global _TICKER_CACHE, _TICKER_CACHE_TS
        now = time.monotonic()
        if now - _TICKER_CACHE_TS < _TICKER_CACHE_TTL and _TICKER_CACHE:
            return _TICKER_CACHE.get("data", [])
        data = await self._get(f"{SPOT_BASE}/api/v3/ticker/24hr")
        if isinstance(data, list):
            _TICKER_CACHE = {"data": data}
            _TICKER_CACHE_TS = now
            return data
        return _TICKER_CACHE.get("data", [])

    # ── fetch top symbols ────────────────────────────────────────
    async def fetch_top_symbols(self, limit: int = 30) -> list[str]:
        """Return top ``limit`` USDT-denominated symbols by 24h quote volume."""
        data = await self._get_all_tickers()
        if not data:
            return self._symbol_cache[:limit] if self._symbol_cache else []

        usdt_pairs = [
            t for t in data
            if t.get("symbol", "").endswith(_QUOTE_ASSET)
            and float(t.get("quoteVolume", 0)) > 0
        ]
        usdt_pairs.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
        symbols = [str(t["symbol"]) for t in usdt_pairs[:limit]]
        self._symbol_cache = symbols
        return symbols

    # ── breakout detection ───────────────────────────────────────
    async def breakout_detected(self, symbol: str) -> bool:
        """Simple Bollinger-band breakout: close > upper band (20-period, 2σ)."""
        klines = await self._get(
            f"{SPOT_BASE}/api/v3/klines",
            {"symbol": symbol, "interval": "15m", "limit": 21},
        )
        if not isinstance(klines, list) or len(klines) < 21:
            return False

        closes = [float(k[4]) for k in klines]
        self._kline_cache[symbol] = klines

        mean = statistics.mean(closes[:-1])
        stdev = statistics.pstdev(closes[:-1])
        if stdev == 0:
            return False

        upper_band = mean + 2 * stdev
        return closes[-1] > upper_band

    # ── funding rate extremes ────────────────────────────────────
    async def fetch_funding_rates(self) -> dict[str, float]:
        """Fetch latest funding rates for all perp symbols."""
        data = await self._get(f"{FUTURES_BASE}/fapi/v1/premiumIndex")
        if not data:
            return self._funding_cache

        rates: dict[str, float] = {}
        for item in data:
            sym = item.get("symbol", "")
            rate = float(item.get("lastFundingRate", 0))
            rates[sym] = rate

        self._funding_cache = rates
        return rates

    async def funding_extreme(self, symbol: str) -> str | None:
        """Return 'FUNDING_SHORT' or 'FUNDING_LONG' if funding rate is extreme."""
        if not self._funding_cache:
            await self.fetch_funding_rates()

        rate = self._funding_cache.get(symbol)
        if rate is None:
            return None

        if rate < -0.0005:  # very negative → shorts are paying longs
            return "FUNDING_SHORT"
        if rate > 0.001:  # very positive → longs are paying shorts
            return "FUNDING_LONG"
        return None

    # ── smart money inflow (approx from large trades) ────────────
    async def smart_money_inflow(self, symbol: str) -> float:
        """Approximate whale activity by summing trades > $50k in last 15m."""
        trades = await self._get(
            f"{SPOT_BASE}/api/v3/trades",
            {"symbol": symbol, "limit": 500},
        )
        if not isinstance(trades, list):
            return 0.0

        total = 0.0
        for t in trades:
            qty = float(t.get("qty", 0))
            price = float(t.get("price", 0))
            value = qty * price
            if value >= 50_000:
                total += value

        return total

    # ── regime classification ────────────────────────────────────
    async def classify_regime(self) -> str:
        """Classify market regime from BTC 1h chart volatility + trend."""
        klines = await self._get(
            f"{SPOT_BASE}/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": "1h", "limit": 25},
        )
        if not isinstance(klines, list) or len(klines) < 20:
            return "unknown"

        closes = [float(k[4]) for k in klines]
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]

        volatility = statistics.pstdev(returns)
        trend = sum(returns[-5:])  # net return over last 5h

        if volatility > 0.008:  # high vol
            return "volatility_expansion" if trend > 0 else "volatility_crash"
        elif abs(trend) < 0.002:
            return "range_bound"
        elif trend > 0:
            return "trending_up"
        else:
            return "trending_down"

    # ── price fetch for dashboard ────────────────────────────────
    async def fetch_prices(self, symbols: list[str]) -> list[dict[str, Any]]:
        """Fetch current prices and 24h change for given symbols (uses cached tickers)."""
        data = await self._get_all_tickers()
        if not data:
            return []

        lookup = {t["symbol"]: t for t in data if t.get("symbol") in symbols}
        result = []
        for sym in symbols:
            t = lookup.get(sym)
            if t:
                result.append({
                    "symbol": sym,
                    "price": f"${float(t['lastPrice']):,.2f}",
                    "change": f"{float(t['priceChangePercent']):+.2f}%",
                    "volume_24h": float(t.get("quoteVolume", 0)),
                })
        return result
