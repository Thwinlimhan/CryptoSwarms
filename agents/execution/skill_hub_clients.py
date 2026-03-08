from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SkillHubTransport(Protocol):
    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float


@dataclass(slots=True)
class BinanceSkillHubClient:
    base_url: str
    transport: SkillHubTransport

    def place_bracket_order(self, intent: OrderIntent) -> dict[str, Any]:
        return self.transport.post(
            self.base_url.rstrip("/") + "/binance/orders/bracket",
            {
                "symbol": intent.symbol,
                "side": intent.side,
                "qty": intent.quantity,
                "entry": intent.entry_price,
                "sl": intent.stop_loss,
                "tp": intent.take_profit,
            },
        )


@dataclass(slots=True)
class HyperliquidSkillHubClient:
    base_url: str
    transport: SkillHubTransport

    def place_bracket_order(self, intent: OrderIntent) -> dict[str, Any]:
        return self.transport.post(
            self.base_url.rstrip("/") + "/hyperliquid/orders/bracket",
            {
                "coin": intent.symbol,
                "is_buy": intent.side.lower() == "buy",
                "size": intent.quantity,
                "entry_price": intent.entry_price,
                "stop_loss": intent.stop_loss,
                "take_profit": intent.take_profit,
            },
        )


@dataclass(slots=True)
class AsterSkillHubClient:
    base_url: str
    transport: SkillHubTransport

    def place_perp_order(self, intent: OrderIntent) -> dict[str, Any]:
        return self.transport.post(
            self.base_url.rstrip("/") + "/aster/perps/order",
            {
                "symbol": intent.symbol,
                "side": intent.side,
                "amount": intent.quantity,
                "entry": intent.entry_price,
                "sl": intent.stop_loss,
                "tp": intent.take_profit,
            },
        )


@dataclass(slots=True)
class OkxSkillHubClient:
    base_url: str
    transport: SkillHubTransport

    def execute_swap(self, *, from_token: str, to_token: str, amount: float, max_price_impact: float = 0.02) -> dict[str, Any]:
        quote = self.transport.post(
            self.base_url.rstrip("/") + "/okx/quote",
            {
                "from_token": from_token,
                "to_token": to_token,
                "amount": amount,
            },
        )
        impact = float(quote.get("price_impact", 1.0))
        if impact > max_price_impact:
            raise ValueError(f"price impact too high: {impact}")
        return self.transport.post(
            self.base_url.rstrip("/") + "/okx/swap",
            {
                "quote_id": quote.get("quote_id"),
                "slippage": 0.005,
            },
        )


@dataclass(slots=True)
class SkillHubExecutionRouter:
    binance: BinanceSkillHubClient
    hyperliquid: HyperliquidSkillHubClient
    aster: AsterSkillHubClient
    okx: OkxSkillHubClient

    def route_perp_order(self, intent: OrderIntent, *, prefer: str = "hyperliquid") -> dict[str, Any]:
        p = prefer.lower()
        if p == "hyperliquid":
            return self.hyperliquid.place_bracket_order(intent)
        if p == "binance":
            return self.binance.place_bracket_order(intent)
        if p == "aster":
            return self.aster.place_perp_order(intent)
        raise ValueError(f"unsupported venue preference: {prefer}")

    def route_dex_swap(self, *, from_token: str, to_token: str, amount: float) -> dict[str, Any]:
        return self.okx.execute_swap(from_token=from_token, to_token=to_token, amount=amount)
