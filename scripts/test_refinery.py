"""
Standalone test: runs the strategy refinery loop with a MockLLM
and prints the resulting MemoryDag nodes.

Does NOT go through cryptoswarms.__init__ to avoid heavy import chain.
"""
import sys, os, json, asyncio, logging

# Add project root so bare imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("test_refinery")

# ── Direct imports (skip __init__.py) ───────────────────────────
from cryptoswarms.memory_dag import MemoryDag
from cryptoswarms.research import prompts

# ── MockLLM ─────────────────────────────────────────────────────
class MockLLM:
    """Returns a realistic refinement proposal JSON for any strategy file."""

    async def complete(self, prompt: str, json_response: bool = False) -> str:
        # Detect which strategy the prompt is about
        if "breakout_trend" in prompt.lower():
            return json.dumps({
                "strategy_id": "breakout_trend",
                "rationale": (
                    "BTC 15m breakout thresholds are too tight for current "
                    "high-volatility regime (ATR 2.8%).  Widening the entry "
                    "band and reducing cooldown will capture 18% more signals "
                    "while keeping stop-loss risk constant."
                ),
                "proposed_parameters": {
                    "breakout_threshold_pct": 0.025,
                    "cooldown_bars": 4,
                    "trailing_stop_pct": 0.012
                },
                "confidence": 0.82
            })
        else:
            return json.dumps({
                "strategy_id": "funding_arbitrage",
                "rationale": (
                    "Funding rate mean has shifted from +0.01% to +0.005% "
                    "over the past 14 days.  Lowering the min_funding_rate "
                    "entry threshold will let the strategy capture 22% more "
                    "opportunities without increasing drawdown."
                ),
                "proposed_parameters": {
                    "min_funding_rate": 0.0004,
                    "max_position_usd": 12000,
                    "hedge_ratio": 0.98
                },
                "confidence": 0.88
            })


# ── Inline refine_strategies (mirrors ResearchAgent.refine_strategies) ──
async def refine_strategies(dag: MemoryDag, llm: MockLLM, history: str) -> None:
    from datetime import datetime, timezone

    strategy_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "strategies"
    )
    if not os.path.exists(strategy_dir):
        logger.warning("Strategy directory not found: %s", strategy_dir)
        return

    for filename in os.listdir(strategy_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            path = os.path.join(strategy_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code = f.read()

                prompt = prompts.STRATEGY_REFINERY.format(code=code, history=history)
                raw = await llm.complete(prompt, json_response=True)
                proposal = json.loads(raw)

                node = dag.add_node(
                    node_type="strategy_refinement",
                    topic=proposal.get("strategy_id", filename),
                    content=f"LLM Refinement Proposal for {filename}: {proposal.get('rationale')}",
                    metadata={
                        "proposed_parameters": proposal.get("proposed_parameters"),
                        "confidence": proposal.get("confidence", 0.0),
                        "source_file": filename,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                logger.info("✓ Generated refinement for %s  [node_id=%s]", filename, node.node_id)
            except Exception as e:
                logger.error("✗ Failed to refine %s: %s", filename, e)


# ── Main ────────────────────────────────────────────────────────
async def main():
    dag = MemoryDag()
    llm = MockLLM()
    history = (
        "Last 24h: BTC volatility spiked 45%, funding rates compressed across "
        "perp markets. Breakout strategy triggered 3x stop-losses. Funding arb "
        "missed 4 entries due to min_funding_rate threshold."
    )

    print("\n" + "="*60)
    print("  STRATEGY REFINERY — TEST RUN")
    print("="*60 + "\n")

    await refine_strategies(dag, llm, history)

    print("\n" + "-"*60)
    print(f"  RESULT: {len(dag.nodes())} refinement nodes generated")
    print("-"*60 + "\n")

    for node in dag.nodes():
        print(f"  +-- NODE  {node.node_id}")
        print(f"  |   Topic : {node.topic}")
        print(f"  |   Source: {node.metadata.get('source_file')}")
        print(f"  |   Conf  : {node.metadata.get('confidence', 0)*100:.0f}%")
        print(f"  |")
        print(f"  |   Proposed Parameters:")
        for k, v in (node.metadata.get("proposed_parameters") or {}).items():
            print(f"  |     {k}: {v}")
        print(f"  |")
        print(f"  |   Rationale:")
        # wrap long rationale
        words = node.content.split()
        line = "  |     "
        for w in words:
            if len(line) + len(w) > 70:
                print(line)
                line = "  |     "
            line += w + " "
        if line.strip():
            print(line)
        print(f"  +{'='*58}\n")

    # Also dump the DAG JSON for verification
    dag_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "test_refinery_dag.json"
    )
    dag.save_json(dag_path)
    print(f"  DAG saved to: {dag_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
