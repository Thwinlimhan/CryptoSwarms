"""Hyperliquid API adapter — compatible with HyPaper and real HL.

In 'paper' mode (via HyPaper), authentication is simplified to just passing the wallet address.
In 'live' mode, standard HL signing is required (not implemented here yet).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from api.settings import settings
from cryptoswarms.execution_router import OrderIntent

logger = logging.getLogger(__name__)

class HyperliquidAdapter:
    """Adapter for Hyperliquid / HyPaper API.
    
    Attributes:
        base_url: The root URL of the HL or HyPaper API (e.g. http://localhost:3001)
        wallet: The 0x... address identifying the account.
    """

    def __init__(self, base_url: Optional[str] = None, wallet: Optional[str] = None):
        self.base_url = (base_url or settings.hyperliquid_api_url).rstrip("/")
        self.wallet = wallet or settings.hyperliquid_wallet
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
        self._asset_map: dict[str, int] = {}

    async def close(self):
        await self._client.aclose()

    async def info(self, request_type: str, **kwargs) -> Any:
        """Post to HL /info endpoint."""
        payload = {"type": request_type, **kwargs}
        try:
            resp = await self._client.post("/info", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Hyperliquid info request failed ({request_type}): {e}")
            return None

    async def exchange(self, action: dict[str, Any]) -> Any:
        """Post to HL /exchange endpoint (compatible with HyPaper wallet field)."""
        # HyPaper expects the wallet in the top level of the body
        payload = {
            "action": action,
            "nonce": 0,
            "signature": {"r": "", "s": "", "v": 0}, # Placeholder
            "wallet": self.wallet
        }
        try:
            resp = await self._client.post("/exchange", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Hyperliquid exchange request failed ({action.get('type')}): {e}")
            return None

    async def get_meta(self) -> Any:
        """Fetch universe metadata (coin -> asset id mapping)."""
        data = await self.info("meta")
        if data and "universe" in data:
            for i, asset in enumerate(data["universe"]):
                self._asset_map[asset["name"]] = i
        return data

    async def get_user_state(self) -> Any:
        """Fetch account balance, positions, etc."""
        return await self.info("clearinghouseState", user=self.wallet)

    async def place_order(
        self, 
        coin: str, 
        is_buy: bool, 
        size: float, 
        limit_px: float, 
        reduce_only: bool = False
    ) -> Any:
        """Place a limit order."""
        if not self._asset_map:
            await self.get_meta()
            
        asset_id = self._asset_map.get(coin)
        if asset_id is None:
            logger.error(f"Unknown coin: {coin}")
            return None

        action = {
            "type": "order",
            "orders": [{
                "a": asset_id,
                "b": is_buy,
                "s": f"{float(size):.8f}".rstrip("0").rstrip("."),
                "p": f"{float(limit_px):.8f}".rstrip("0").rstrip("."),
                "t": {"limit": {"tif": "Gtc"}},
                "r": reduce_only
            }],
            "grouping": "na"
        }
        return await self.exchange(action)

    async def cancel_order(self, coin: str, oid: int) -> Any:
        """Cancel an existing order."""
        if not self._asset_map:
            await self.get_meta()
            
        asset_id = self._asset_map.get(coin)
        action = {
            "type": "cancel",
            "cancels": [{"asset": asset_id, "oid": oid}]
        }
        return await self.exchange(action)

    async def get_order_status(self, oid: int | str) -> dict[str, Any] | None:
        """Fetch status of a specific order."""
        # For HL, we can check open orders in user state
        user_state = await self.get_user_state()
        if not user_state:
            return None
            
        # Check open orders
        for order in user_state.get("openOrders", []):
            if str(order.get("oid")) == str(oid):
                return {
                    "status": "open",
                    "oid": order.get("oid"),
                    "symbol": order.get("coin"),
                    "limit_px": order.get("limitPx"),
                    "sz": order.get("sz"),
                }
        
        # If not in open orders, it might be filled or cancelled.
        # Ideally we'd check trade history here.
        # For now, let's assume if it's not open, it's 'closed'
        return {"status": "closed", "oid": oid}

    async def execute(self, intent: OrderIntent, reduce_only: bool = False) -> Any:
        """Implementation of OrderExecutor protocol."""
        # Simple market-ish limit order (taking 1% slippage for immediate fill in paper)
        side = intent.side.upper()
        is_buy = side == "BUY" or side == "LONG"
        
        # We need a price to place a limit order. For paper, we can fetch the mid.
        meta = await self.info("allMids")
        price = float((meta or {}).get(intent.symbol, 0))
        if price == 0:
            logger.error(f"Cannot execute order: no price for {intent.symbol}")
            return None

        # 1% slippage
        limit_px = price * 1.01 if is_buy else price * 0.99
        
        return await self.place_order(
            coin=intent.symbol,
            is_buy=is_buy,
            size=intent.quantity,
            limit_px=limit_px,
            reduce_only=reduce_only or intent.reduce_only
        )
