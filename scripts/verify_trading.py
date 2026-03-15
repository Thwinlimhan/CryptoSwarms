import asyncio
import logging
import json
import httpx
from datetime import datetime
from cryptoswarms.adapters.hyperliquid_adapter import HyperliquidAdapter
from cryptoswarms.execution_router import OrderIntent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_trading")

async def verify_trading_flow():
    """
    Simulate a trading decision and verify it reaches the Hyperliquid paper backend.
    """
    logger.info("Starting Trading Domain Verification...")
    
    # 1. Initialize Adapter
    adapter = HyperliquidAdapter()
    
    # 2. Mock a strategic decision (as if from AgentRunner)
    # Symbol: SOL
    # Action: BUY
    # Size: 1.0 SOL
    intent = OrderIntent(
        symbol="SOL",
        side="BUY",
        quantity=1.0
    )
    
    logger.info(f"Triggering mock execution: {intent.side} {intent.quantity} {intent.symbol}")
    
    try:
        # 3. Execute trade
        await adapter.execute(intent)
        logger.info("Execution command sent successfully.")
        
        # 4. Verify against HyPaper Backend
        logger.info("Checking HyPaper backend for open positions...")
        data = await adapter.get_user_state()
        
        if data:
            # assetPositions is inside the response
            # In real HL it's often nested under "assetPositions"
            positions = data.get("assetPositions", [])
            logger.info(f"Current Positions: {json.dumps(positions, indent=2)}")
            
            # Look for SOL position
            # Note: in HL wire format it might be different, 
            # but HyPaper humanizes the coin name in clearinghouseState response
            sol_pos = next((p for p in positions if p["position"]["coin"] == "SOL"), None)
            if sol_pos:
                logger.info("✅ PROOF: SOL position found in Hyperliquid paper backend!")
                size = sol_pos["position"]["szi"]
                logger.info(f"Position Size: {size}")
            else:
                logger.warning("❌ No SOL position found yet. (Execution might be async or backend processing delayed)")
        else:
            logger.error("Failed to query HyPaper user state.")

    except Exception as e:
        logger.error(f"Verification failed with error: {e}")
    finally:
        await adapter.close()
        logger.info("Verification script finished.")

if __name__ == "__main__":
    asyncio.run(verify_trading_flow())
