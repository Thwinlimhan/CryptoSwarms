from __future__ import annotations

from dataclasses import dataclass

from agents.execution.skill_hub_clients import (
    AsterSkillHubClient,
    BinanceSkillHubClient,
    HyperliquidSkillHubClient,
    OkxSkillHubClient,
    OrderIntent,
    SkillHubExecutionRouter,
)


@dataclass
class FakeTransport:
    calls: list[tuple[str, dict]]

    def post(self, url: str, payload: dict):
        self.calls.append((url, payload))
        if url.endswith("/okx/quote"):
            return {"quote_id": "q-1", "price_impact": 0.01}
        return {"status": "ok", "url": url}


def _router() -> tuple[SkillHubExecutionRouter, FakeTransport]:
    t = FakeTransport(calls=[])
    router = SkillHubExecutionRouter(
        binance=BinanceSkillHubClient("http://skills", t),
        hyperliquid=HyperliquidSkillHubClient("http://skills", t),
        aster=AsterSkillHubClient("http://skills", t),
        okx=OkxSkillHubClient("http://skills", t),
    )
    return router, t


def test_router_routes_hyperliquid_perp_order():
    router, t = _router()
    result = router.route_perp_order(
        OrderIntent("BTC", "buy", 0.1, 60000, 59000, 62000),
        prefer="hyperliquid",
    )

    assert result["status"] == "ok"
    assert any(url.endswith("/hyperliquid/orders/bracket") for url, _ in t.calls)


def test_router_routes_binance_perp_order():
    router, t = _router()
    router.route_perp_order(OrderIntent("BTCUSDT", "buy", 0.2, 60000, 59000, 62000), prefer="binance")
    assert any(url.endswith("/binance/orders/bracket") for url, _ in t.calls)


def test_router_okx_swap_checks_impact_then_executes():
    router, t = _router()
    result = router.route_dex_swap(from_token="ETH", to_token="USDC", amount=1000)

    assert result["status"] == "ok"
    urls = [u for u, _ in t.calls]
    assert urls[-2].endswith("/okx/quote")
    assert urls[-1].endswith("/okx/swap")


def test_okx_swap_rejects_high_impact():
    class BadImpactTransport(FakeTransport):
        def post(self, url: str, payload: dict):
            self.calls.append((url, payload))
            if url.endswith("/okx/quote"):
                return {"quote_id": "q-2", "price_impact": 0.2}
            return {"status": "ok"}

    t = BadImpactTransport(calls=[])
    client = OkxSkillHubClient("http://skills", t)

    try:
        client.execute_swap(from_token="ETH", to_token="USDC", amount=500)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "price impact" in str(exc)
