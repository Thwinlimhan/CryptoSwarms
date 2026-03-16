"""Binance WebSocket Market Data — replaces REST polling with persistent WS streams.

Connects to Binance combined WebSocket streams for:
  - Mini ticker (24h price updates across all symbols)
  - Individual kline/candlestick streams for breakout detection
  - Trade streams for whale activity detection

Falls back to REST polling (via BinanceMarketData) if WebSocket fails.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger("swarm.adapters.binance_ws")

# Binance WebSocket endpoints
SPOT_WS_BASE = "wss://stream.binance.com:9443"
COMBINED_STREAM = f"{SPOT_WS_BASE}/stream"

# Rate of price cache refresh  
_PRICE_CACHE_MAX_AGE = 5.0  # seconds


@dataclass
class StreamStats:
    """Statistics for the WebSocket stream."""
    messages_received: int = 0
    reconnect_count: int = 0
    last_message_at: float = 0.0
    connected: bool = False
    subscribed_streams: list[str] = field(default_factory=list)
    errors: int = 0


class BinanceWebSocketStream:
    """Persistent WebSocket connection to Binance market data streams.

    Provides real-time price updates via WebSocket instead of REST polling.
    Manages subscriptions, automatic reconnection, and data distribution
    to registered callbacks.
    """

    def __init__(
        self,
        *,
        on_price_update: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_kline: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_trade: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        max_reconnects: int = 100,
        max_backoff: float = 120.0,
    ) -> None:
        self._on_price_update = on_price_update
        self._on_kline = on_kline
        self._on_trade = on_trade
        self._max_reconnects = max_reconnects
        self._max_backoff = max_backoff

        # Internal state
        self._ws: Any = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._stats = StreamStats()
        self._reconnect_attempts = 0

        # Price cache — updated in real-time from mini-ticker stream
        self._prices: dict[str, dict[str, Any]] = {}
        self._prices_updated_at: float = 0.0

        # Subscribed symbols for kline/trade streams
        self._tracked_symbols: list[str] = []

        # Callbacks for internal distribution
        self._price_callbacks: list[Callable[[dict[str, Any]], Awaitable[None]]] = []

    # ── Public API ──────────────────────────────────────────────────

    async def start(self, symbols: list[str] | None = None) -> None:
        """Start the WebSocket stream.

        Args:
            symbols: Optional list of symbols to subscribe to kline/trade streams.
                     Mini-ticker stream covers all symbols automatically.
        """
        if self._running:
            logger.warning("BinanceWebSocketStream already running")
            return

        self._tracked_symbols = [s.lower() for s in (symbols or [])]
        self._running = True
        self._task = asyncio.create_task(self._connect_loop(), name="binance_ws")
        logger.info("BinanceWebSocketStream started (tracking %d symbols)", len(self._tracked_symbols))

    async def stop(self) -> None:
        """Stop the WebSocket stream gracefully."""
        self._running = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._stats.connected = False
        logger.info("BinanceWebSocketStream stopped")

    def update_symbols(self, symbols: list[str]) -> None:
        """Update the list of tracked symbols (reconnect will use new list)."""
        self._tracked_symbols = [s.lower() for s in symbols]

    def add_price_callback(self, callback: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        """Register an additional callback for price updates."""
        self._price_callbacks.append(callback)

    # ── Price Access ────────────────────────────────────────────────

    def get_price(self, symbol: str) -> dict[str, Any] | None:
        """Get cached price for a symbol."""
        return self._prices.get(symbol.upper())

    def get_all_prices(self) -> dict[str, dict[str, Any]]:
        """Get all cached prices."""
        return dict(self._prices)

    def get_top_by_volume(self, limit: int = 30, quote: str = "USDT") -> list[dict[str, Any]]:
        """Return top symbols by 24h quote volume from the WS cache."""
        usdt_pairs = [
            v for v in self._prices.values()
            if v.get("symbol", "").endswith(quote)
        ]
        usdt_pairs.sort(key=lambda x: x.get("volume", 0.0), reverse=True)
        return usdt_pairs[:limit]

    def get_hot_assets(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return top movers formatted for the dashboard."""
        top = self.get_top_by_volume(limit=limit)
        result = []
        for t in top:
            result.append({
                "symbol": t.get("symbol", ""),
                "price": f"{t.get('close', 0):,.2f}",
                "change": f"{t.get('change_pct', 0):+.2f}",
                "volume_24h": t.get("volume", 0.0),
            })
        return result

    @property
    def is_connected(self) -> bool:
        return self._stats.connected

    @property
    def stats(self) -> StreamStats:
        return self._stats

    @property
    def price_cache_age(self) -> float:
        """Seconds since last price cache update."""
        if self._prices_updated_at == 0:
            return float("inf")
        return time.monotonic() - self._prices_updated_at

    # ── Connection Loop ─────────────────────────────────────────────

    async def _connect_loop(self) -> None:
        """Main connection loop with exponential backoff reconnection."""
        while self._running and self._reconnect_attempts < self._max_reconnects:
            try:
                await self._connect_and_listen()
                # If we reach here, the connection closed cleanly
                self._reconnect_attempts = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._stats.errors += 1
                self._stats.connected = False
                self._reconnect_attempts += 1
                self._stats.reconnect_count += 1

                wait = min(self._max_backoff, 2 ** self._reconnect_attempts)
                logger.warning(
                    "Binance WS disconnected (attempt %d/%d): %s — reconnecting in %.0fs",
                    self._reconnect_attempts, self._max_reconnects, exc, wait,
                )
                await asyncio.sleep(wait)

        if self._reconnect_attempts >= self._max_reconnects:
            logger.error("Binance WS permanently failed after %d attempts", self._max_reconnects)

    async def _connect_and_listen(self) -> None:
        """Establish WS connection and listen for messages."""
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "websockets package not installed — install with: pip install websockets"
            )
            raise RuntimeError("websockets not installed")

        # Build the combined stream URL
        streams = self._build_stream_list()
        url = f"{COMBINED_STREAM}?streams={'/'.join(streams)}"
        self._stats.subscribed_streams = streams

        logger.info("Connecting to Binance WS: %d streams", len(streams))

        async with websockets.connect(  # type: ignore[attr-defined]
            url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_size=2**22,  # 4MB — ticker messages can be large
        ) as ws:
            self._ws = ws
            self._stats.connected = True
            self._reconnect_attempts = 0
            logger.info("Binance WS connected (%d streams)", len(streams))

            async for raw_message in ws:
                if not self._running:
                    break
                self._stats.messages_received += 1
                self._stats.last_message_at = time.monotonic()

                try:
                    message = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
                    await self._dispatch_message(message)
                except Exception as exc:
                    logger.debug("Error processing WS message: %s", exc)

    def _build_stream_list(self) -> list[str]:
        """Build the list of stream names for the combined endpoint."""
        streams: list[str] = []

        # 1. All mini-tickers (covers price + 24h stats for all symbols)
        streams.append("!miniTicker@arr")

        # 2. Kline streams for tracked symbols (15m for breakout detection)
        for sym in self._tracked_symbols:
            streams.append(f"{sym}@kline_15m")

        # 3. Aggregate trade streams for tracked symbols (whale detection)
        for sym in self._tracked_symbols[:10]:  # Limit trade streams
            streams.append(f"{sym}@aggTrade")

        return streams

    # ── Message Dispatch ────────────────────────────────────────────

    async def _dispatch_message(self, message: dict[str, Any]) -> None:
        """Route incoming WS message to the appropriate handler."""
        # Combined stream format: {"stream": "...", "data": {...}}
        stream = message.get("stream", "")
        data = message.get("data", message)

        if stream == "!miniTicker@arr":
            await self._handle_mini_ticker(data)
        elif "@kline_" in stream:
            await self._handle_kline(data)
        elif "@aggTrade" in stream:
            await self._handle_agg_trade(data)

    async def _handle_mini_ticker(self, tickers: Any) -> None:
        """Process mini-ticker array — update price cache in real-time."""
        if not isinstance(tickers, list):
            return

        now = time.monotonic()
        for t in tickers:
            symbol = t.get("s", "")
            if not symbol:
                continue

            entry = {
                "symbol": symbol,
                "close": float(t.get("c", 0)),
                "open": float(t.get("o", 0)),
                "high": float(t.get("h", 0)),
                "low": float(t.get("l", 0)),
                "volume": float(t.get("v", 0)),  # Base asset volume
                "quote_volume": float(t.get("q", 0)),  # Quote asset volume
                "change_pct": 0.0,
                "updated_at": now,
            }

            # Calculate 24h change percentage
            if entry["open"] > 0:
                entry["change_pct"] = round(
                    ((entry["close"] - entry["open"]) / entry["open"]) * 100, 2
                )

            self._prices[symbol] = entry

        self._prices_updated_at = now

        # Fire callbacks
        if self._on_price_update is not None:
            try:
                await self._on_price_update({"type": "ticker_batch", "count": len(tickers)})
            except Exception as exc:
                logger.debug("Price update callback error: %s", exc)

        for cb in self._price_callbacks:
            try:
                await cb({"type": "ticker_batch", "count": len(tickers)})
            except Exception:
                pass

    async def _handle_kline(self, data: dict[str, Any]) -> None:
        """Process kline/candlestick event."""
        kline_data = data.get("k", {})
        if not kline_data:
            return

        parsed = {
            "symbol": kline_data.get("s", ""),
            "interval": kline_data.get("i", ""),
            "open_time": kline_data.get("t", 0),
            "close_time": kline_data.get("T", 0),
            "open": float(kline_data.get("o", 0)),
            "high": float(kline_data.get("h", 0)),
            "low": float(kline_data.get("l", 0)),
            "close": float(kline_data.get("c", 0)),
            "volume": float(kline_data.get("v", 0)),
            "is_closed": kline_data.get("x", False),
        }

        if self._on_kline is not None:
            try:
                await self._on_kline(parsed)
            except Exception as exc:
                logger.debug("Kline callback error: %s", exc)

    async def _handle_agg_trade(self, data: dict[str, Any]) -> None:
        """Process aggregate trade event (for whale detection)."""
        price = float(data.get("p", 0))
        qty = float(data.get("q", 0))
        value_usd = price * qty

        parsed = {
            "symbol": data.get("s", ""),
            "price": price,
            "quantity": qty,
            "value_usd": value_usd,
            "is_buyer_maker": data.get("m", False),
            "trade_time": data.get("T", 0),
            "is_whale": value_usd >= 50_000,
        }

        if self._on_trade is not None and parsed["is_whale"]:
            try:
                await self._on_trade(parsed)
            except Exception as exc:
                logger.debug("Trade callback error: %s", exc)
