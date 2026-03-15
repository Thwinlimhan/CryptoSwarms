import asyncio
import logging
from datetime import datetime, timezone
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat
from cryptoswarms.memory_dag import MemoryDag
from cryptoswarms.research_agent import ResearchAgent
from api.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_research")

async def verify_research_loop():
    logger.info("Initializing Research Agent verification...")
    
    # Setup dependencies
    dsn = f"postgres://{settings.timescaledb_user}:{settings.timescaledb_password}@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    db = TimescaleSink(dsn)
    await db.connect()
    
    import json
    from cryptoswarms.adapters.llm import LLMClient
    
    heartbeat = RedisHeartbeat(settings.redis_url)
    dag = MemoryDag()
    
    # Mock LLM to test the prompt logic
    class MockLLM(LLMClient):
        def __init__(self):
            pass # No need for settings in mock
        async def complete(self, prompt: str, **kwargs) -> str:
            p_upper = prompt.upper()
            if "EXPERIMENT_GENERATOR" in p_upper or "VARIABLE" in p_upper or "THEME" in p_upper:
                return json.dumps({
                    "experiments": [
                        {
                            "variable": "scanner_breakout_confidence",
                            "baseline_value": "0.78",
                            "variant_value": "0.85",
                            "hypothesis": "Low confidence leads to noise"
                        }
                    ],
                    "score": 0.92,
                    "delta_vs_baseline": 0.12,
                    "metrics": {"quality": 0.95, "latency": 0.05, "token_efficiency": 0.9},
                    "log": "LLM simulation successful",
                    "summary": "Swarm is performing well but needs higher confidence thresholds.",
                    "recommendation": "Increase confidence to 0.85",
                    "regressions": "None",
                    "safety_note": "Proceed with caution"
                })
            return "{}"

    agent = ResearchAgent(db=db, heartbeat=heartbeat, dag=dag, llm=MockLLM())
    
    # 1. Insert some mock history for the agent to "study"
    logger.info("Inserting mock swarm history...")
    await db.write_signal(
        agent_name="scanner_alpha",
        signal_type="breakout",
        symbol="BTC",
        confidence=0.85,
        metadata={"volume_spike": 2.1}
    )
    
    import uuid
    decision_id = str(uuid.uuid4())
    await db.write_decision({
        "id": decision_id,
        "label": "BUY BTC",
        "strategy_id": "momentum_v1",
        "symbol": "BTC",
        "ev_estimate": 0.05,
        "win_probability": 0.6,
        "position_size_usd": 100,
        "status": "resolved"
    })
    # Resolve it with profit
    await db.resolve_decision(
        decision_id=decision_id,
        status="success",
        pnl=10.5,
        notes="Strong fill"
    )

    # 2. Force start the nightly research cycle (bypassing time check)
    logger.info("Simulating nightly research execution...")
    await agent.run_nightly_research()
    
    # 3. Verify results
    logger.info("Verifying research output...")
    experiments = await db.get_recent_experiments(limit=5)
    reports = await db.get_recent_reports(limit=1)
    
    if reports:
        logger.info(f"✅ PROOF: Research report generated: {reports[0]['summary']}")
        logger.info(f"Recommendation: {reports[0]['recommendation']}")
    else:
        logger.error("❌ No research report found.")
        
    if experiments:
        logger.info(f"✅ PROOF: {len(experiments)} isolated experiments recorded.")
        for e in experiments:
            logger.info(f"Experiment: {e['variable']} -> {e['variant_value']} (Score: {e['score']})")
    else:
        logger.error("❌ No experiments found.")

    await db.close()
    logger.info("Verification complete.")

async def patch_db_methods(db):
    # Add helper for verification script
    async def get_recent_experiments(limit: int = 5):
        rows = await db._pool.fetch("SELECT * FROM research_experiments ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]
    async def get_recent_reports(limit: int = 1):
        rows = await db._pool.fetch("SELECT * FROM research_reports ORDER BY created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]
    db.get_recent_experiments = get_recent_experiments
    db.get_recent_reports = get_recent_reports

if __name__ == "__main__":
    # Small hack to add verification methods without editing the class again
    dsn = f"postgres://{settings.timescaledb_user}:{settings.timescaledb_password}@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    db = TimescaleSink(dsn)
    
    async def run():
        await db.connect()
        await patch_db_methods(db)
        # Re-initialize agent with patched db if needed, or just use the patched db
        # Actually, let's just use the loop
        await verify_research_loop()
        
    asyncio.run(run())
