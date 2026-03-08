from agents.execution.skill_hub_clients import (
    AsterSkillHubClient,
    BinanceSkillHubClient,
    HyperliquidSkillHubClient,
    OkxSkillHubClient,
    OrderIntent,
    SkillHubExecutionRouter,
)


class DemoTransport:
    def post(self, url: str, payload: dict):
        if url.endswith('/okx/quote'):
            return {'quote_id': 'demo', 'price_impact': 0.01}
        return {'status': 'ok', 'url': url, 'payload': payload}


def main() -> None:
    transport = DemoTransport()
    router = SkillHubExecutionRouter(
        binance=BinanceSkillHubClient('http://skills.local', transport),
        hyperliquid=HyperliquidSkillHubClient('http://skills.local', transport),
        aster=AsterSkillHubClient('http://skills.local', transport),
        okx=OkxSkillHubClient('http://skills.local', transport),
    )

    perp = router.route_perp_order(OrderIntent('BTCUSDT', 'buy', 0.1, 60000, 59000, 62000), prefer='hyperliquid')
    swap = router.route_dex_swap(from_token='ETH', to_token='USDC', amount=1000)

    print({'perp': perp, 'swap': swap})


if __name__ == '__main__':
    main()
