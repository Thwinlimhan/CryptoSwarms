"""CLI Runner for Backtests.

Downloads 90 days of 15m candles from Binance and replays them through 
the chosen strategy to calculate real-world performance metrics.
"""
import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptoswarms.backtest_engine import BacktestEngine
from cryptoswarms.pipeline.strategy_loader import StrategyLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backtest.runner")

async def fetch_historical_candles(symbol: str, interval: str = "15m", days: int = 30):
    """Fetch candles from Binance SPOT API."""
    logger.info(f"Fetching {days} days of {interval} candles for {symbol}...")
    
    base_url = "https://api.binance.com/api/v3/klines"
    all_candles = []
    
    # Binance limits to 1000 candles per request
    # 30 days of 15m candles = 30 * 24 * 4 = 2880 candles
    # We need to loop.
    
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    
    current_start = start_time
    async with httpx.AsyncClient(timeout=30.0) as client:
        while current_start < end_time:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_time,
                "limit": 1000
            }
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                break
                
            all_candles.extend(data)
            # Next start is the time of the last candle + 1ms
            current_start = data[-1][0] + 1
            
            if len(data) < 1000:
                break
    
    logger.info(f"Downloaded {len(all_candles)} candles.")
    return all_candles

async def main():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    days = 30 
    
    # 1. Load Strategy
    loader = StrategyLoader()
    strategies = loader.load_all()
    
    # Select strategy from CLI or run all
    target_strat = sys.argv[1] if len(sys.argv) > 1 else None
    
    if target_strat:
        if target_strat not in strategies:
            logger.error(f"Strategy {target_strat} not found. Available: {list(strategies.keys())}")
            return
        run_list = [target_strat]
    else:
        run_list = list(strategies.keys())

    # 3. Initialize Engine (One engine for all symbols to track total bankroll)
    engine = BacktestEngine(base_bankroll=10000.0)
    
    for strat_id in run_list:
        strategy = strategies[strat_id]
        print("\n" + "="*60)
        print(f"  RUNNING BACKTEST: {strategy.config.name} ({strat_id})")
        print(f"  SYMBOLS: {', '.join(symbols)} | PERIOD: {days} days")
        print("="*60 + "\n")

        for symbol in symbols:
            # 2. Fetch Data
            try:
                candles = await fetch_historical_candles(symbol, days=days)
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                continue

            # 4. Run Backtest
            await engine.run(strategy, candles, symbol)
    
    # 5. Output Final Results
    results = engine.pm.summary()
    print("\n" + "-"*60)
    print("  FINAL AGGREGATED RESULTS")
    print("-"*60)
    for k, v in results.items():
        print(f"  {k.replace('_', ' ').title():<20}: {v}")
    print("-" * 60 + "\n")

    # If successful, save to a file for the user to review
    report_file = f"data/backtest_report_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    os.makedirs("data", exist_ok=True)
    with open(report_file, "w") as f:
        f.write(f"Multi-Asset Backtest Report: {strategy.config.name}\n")
        f.write(f"Symbols: {', '.join(symbols)}\n")
        f.write(f"Period: {days} days\n\n")
        for k, v in results.items():
            f.write(f"{k}: {v}\n")
            
    print(f"Detailed aggregated report saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())
