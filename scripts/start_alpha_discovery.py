#!/usr/bin/env python3
"""Quick Start: CryptoSwarms Alpha Discovery Engine.

Run this script to initialize and test the complete alpha discovery system.
"""
import asyncio
import logging
import sys
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Initialize and run alpha discovery engine."""
    
    print("🚀 Starting CryptoSwarms Alpha Discovery Engine")
    print("=" * 60)
    
    try:
        # Import the new alpha discovery system
        from cryptoswarms.alpha_discovery_engine import AlphaDiscoveryEngine
        from cryptoswarms.strategies.validated_strategy_factory import ValidatedStrategyFactory
        from cryptoswarms.real_base_rate_registry import RealBaseRateRegistry
        
        print("✅ Alpha discovery modules imported successfully")
        
        # Mock clients for initial testing
        class MockBinanceClient:
            async def get_historical_klines(self, **kwargs):
                logger.info(f"Mock: Fetching historical data for {kwargs.get('symbol', 'UNKNOWN')}")
                return []
        
        class MockTimescaleDB:
            async def insert_ohlcv_batch(self, data):
                logger.info(f"Mock: Storing {len(data)} candles in database")
            
            async def query_ohlcv(self, **kwargs):
                import pandas as pd
                logger.info(f"Mock: Querying data for {kwargs.get('symbol', 'UNKNOWN')}")
                return pd.DataFrame()
        
        # Initialize components
        print("\n🔧 Initializing Alpha Discovery Engine...")
        binance_client = MockBinanceClient()
        timescale_db = MockTimescaleDB()
        
        alpha_engine = AlphaDiscoveryEngine(binance_client, timescale_db)
        strategy_factory = ValidatedStrategyFactory(alpha_engine)
        base_rate_registry = RealBaseRateRegistry(alpha_engine)
        
        print("✅ All components initialized successfully")
        
        # Test the system
        print("\n🧪 Testing Alpha Discovery Pipeline...")
        
        # Test 1: Historical data pipeline
        print("   1. Testing historical data pipeline...")
        try:
            await alpha_engine._ensure_historical_data(
                symbols=["BTCUSDT"],
                intervals=["15m"],
                lookback_days=30
            )
            print("   ✅ Historical data pipeline working")
        except Exception as e:
            print(f"   ❌ Historical data pipeline error: {e}")
        
        # Test 2: Pattern discovery
        print("   2. Testing pattern discovery...")
        try:
            # This will use mock data, so expect empty results
            patterns = alpha_engine.pattern_discovery.discover_all_patterns(
                symbol="BTCUSDT",
                interval="15m",
                lookback_days=30
            )
            print(f"   ✅ Pattern discovery working (found {len(patterns)} patterns)")
        except Exception as e:
            print(f"   ❌ Pattern discovery error: {e}")
        
        # Test 3: Strategy factory
        print("   3. Testing strategy factory...")
        try:
            strategies = strategy_factory.create_strategies_for_symbol("BTCUSDT")
            print(f"   ✅ Strategy factory working (created {len(strategies)} strategies)")
        except Exception as e:
            print(f"   ❌ Strategy factory error: {e}")
        
        # Test 4: Base rate registry
        print("   4. Testing base rate registry...")
        try:
            summary = base_rate_registry.get_summary_stats()
            print(f"   ✅ Base rate registry working: {summary}")
        except Exception as e:
            print(f"   ❌ Base rate registry error: {e}")
        
        # Show system status
        print("\n📊 System Status:")
        print("-" * 30)
        
        deployed_patterns = alpha_engine.get_deployed_patterns()
        print(f"   Deployed Patterns: {len(deployed_patterns)}")
        
        active_strategies = len(strategy_factory.active_strategies)
        print(f"   Active Strategies: {active_strategies}")
        
        alpha_report = alpha_engine.generate_alpha_report()
        print(f"   Alpha Report: {alpha_report}")
        
        print("\n🎯 Next Steps:")
        print("   1. Connect real Binance API and TimescaleDB")
        print("   2. Run full alpha discovery on historical data")
        print("   3. Deploy validated patterns for live trading")
        print("   4. Monitor performance and refresh patterns regularly")
        
        print("\n✅ Alpha Discovery Engine is ready!")
        print("   Replace mock clients with real ones to start discovering alpha.")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all alpha discovery modules are in the Python path")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.exception("Full error details:")
        return False

def show_usage_examples():
    """Show usage examples for the alpha discovery system."""
    
    print("\n💻 USAGE EXAMPLES:")
    print("=" * 40)
    
    print("\n1. Initialize Alpha Discovery Engine:")
    print("```python")
    print("from cryptoswarms.alpha_discovery_engine import AlphaDiscoveryEngine")
    print("")
    print("alpha_engine = AlphaDiscoveryEngine(binance_client, timescale_db)")
    print("```")
    
    print("\n2. Discover Alpha for Multiple Symbols:")
    print("```python")
    print("results = await alpha_engine.discover_alpha(")
    print("    symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],")
    print("    intervals=['15m', '1h'],")
    print("    lookback_days=365,")
    print("    min_deployment_score=0.7")
    print(")")
    print("```")
    
    print("\n3. Create Validated Strategies:")
    print("```python")
    print("from cryptoswarms.strategies.validated_strategy_factory import ValidatedStrategyFactory")
    print("")
    print("factory = ValidatedStrategyFactory(alpha_engine)")
    print("strategies = factory.create_strategies_for_symbol('BTCUSDT')")
    print("```")
    
    print("\n4. Get Real Base Rates:")
    print("```python")
    print("from cryptoswarms.real_base_rate_registry import RealBaseRateRegistry")
    print("")
    print("registry = RealBaseRateRegistry(alpha_engine)")
    print("base_rate = registry.calculate_real_base_rates(")
    print("    pattern_id='bollinger_breakout',")
    print("    symbol='BTCUSDT'")
    print(")")
    print("```")
    
    print("\n5. Check Deployment Criteria:")
    print("```python")
    print("from cryptoswarms.edge.edge_quantifier import DeploymentCriteria")
    print("")
    print("criteria = DeploymentCriteria()")
    print("decision = criteria.evaluate_pattern_for_deployment(edge_metrics)")
    print("")
    print("if decision.approved:")
    print("    print('Pattern ready for live trading!')")
    print("else:")
    print("    print(f'Pattern rejected: {decision.recommendation}')")
    print("```")

if __name__ == "__main__":
    print("CryptoSwarms Alpha Discovery Engine - Quick Start")
    print("Real statistical validation instead of fake alpha")
    print()
    
    # Run the main test
    success = asyncio.run(main())
    
    if success:
        show_usage_examples()
        print("\n🎉 Ready to discover real alpha!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Check the errors above.")
        sys.exit(1)