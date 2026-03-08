# Exchange Skill Hub Integration

Runtime modules now include Skill Hub clients and routing for:
- Binance skill hub bracket orders
- Hyperliquid MCP bracket orders
- Aster perp order path
- OKX DEX quote+swap with impact guard

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\run_exchange_skill_hub_smoke.py
```

Notes:
- Transport is injectable, so the same API can use HTTP, MCP bridge wrappers, or mock transports.
- OKX route enforces price impact check before swap execution.
