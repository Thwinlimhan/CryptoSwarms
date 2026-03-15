"""Swarm Autoresearcher Agent — the observer that studies and improves the swarm.

Implements Karpathy's Autoresearch pattern:
- Nightly isolated experiments on real history
- Evaluates prompt structure, boot context, config values
- Reports findings for human approval
"""

from __future__ import annotations

import logging
import json
import asyncio
import os
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional

from cryptoswarms.common.base_agent import BaseAgent
from cryptoswarms.common.stream_bus import StreamBus
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat
from cryptoswarms.memory_dag import MemoryDag
from cryptoswarms.adapters.llm import LLMClient
from cryptoswarms.research import prompts

logger = logging.getLogger("research_agent")

class ResearchAgent(BaseAgent):
    """Observer agent that runs nightly experiments to optimize the swarm."""

    def __init__(
        self,
        *,
        db: TimescaleSink,
        heartbeat: RedisHeartbeat,
        dag: MemoryDag,
        llm: Optional[LLMClient] = None,
        stream_bus: StreamBus | None = None
    ) -> None:
        super().__init__("swarm_researcher", stream_bus)
        self.db = db
        self.heartbeat_adapter = heartbeat
        self.dag = dag
        self.llm = llm or LLMClient()
        self.is_research_window = False
        self.last_run: datetime | None = None
        
        # Hard Rules from prompt
        self.HARD_RULES = [
            "Never auto-apply production changes",
            "Never test more than one variable at a time",
            "Never run during active hours",
            "Human approval required before live change"
        ]

    async def run_cycle(self) -> None:
        """Check if we are in the quiet window and run experiments if so."""
        now = datetime.now(timezone.utc)
        
        # 1. Identify quiet window (simulated: 02:00 to 04:00 UTC)
        if time(2, 0) <= now.time() <= time(4, 0):
            if self.last_run is None or self.last_run.date() < now.date():
                logger.info("Quiet window detected. Starting nightly research cycle...")
                await self.run_nightly_research()
                self.last_run = now
        
        await self.heartbeat_adapter.set_heartbeat(self.agent_id)
        self.heartbeat(status="researching" if self.is_research_window else "observing")

    async def run_nightly_research(self) -> None:
        """Execute the full autoresearch loop."""
        self.is_research_window = True
        theme = "performance_calibration" # Theme for the night
        
        # 1. Mine history
        history_context = await self.mine_swarm_history()
        
        # 2. Refine existing strategies based on performance
        await self.refine_strategies(history_context)
        
        # 3. Generate experiments
        experiments = await self.generate_experiments(theme, history_context)
        
        # 3. Parallel Execution
        tasks = [self.run_experiment(exp, history_context) for exp in experiments]
        results = await asyncio.gather(*tasks)
        
        # 4. Record Experiments and update DAG
        for res in results:
            await self.db.write_research_experiment(res)
            self.dag.add_node(
                node_type="research_observation",
                topic=res["variable"],
                content=f"Experiment on {res['variable']}: variant {res['variant_value']} scored {res['score']:.2f}",
                metadata=res
            )
            
        # 5. Compile & Record Report
        final_results = list(results)
        report = await self.compile_report(theme, final_results)
        await self.db.write_research_report(report)
        
        logger.info(f"Nightly research complete. Theme: {theme}, Experiments: {len(results)}")
        self.is_research_window = False

    async def mine_swarm_history(self) -> str:
        """Pull history from TimescaleDB and format it for the LLM."""
        signals = await self.db.get_recent_signals(limit=200)
        decisions = await self.db.get_recent_decisions(limit=100)
        
        history_summary = {
            "signal_count": len(signals),
            "decision_count": len(decisions),
            "avg_confidence": sum(s["confidence"] for s in signals) / len(signals) if signals else 0,
            "win_rate": len([d for d in decisions if d.get("pnl_usd", 0) > 0]) / len(decisions) if decisions else 0
        }
        return json.dumps(history_summary)

    async def generate_experiments(self, theme: str, history: str) -> List[Dict[str, Any]]:
        """Identify variables and variants for testing using LLM."""
        prompt = prompts.EXPERIMENT_GENERATOR.format(history=history)
        try:
            raw = await self.llm.complete(prompt, json_response=True)
            data: Dict[str, Any] = json.loads(raw)
            experiments = data.get("experiments", [])
            for e in experiments:
                e["theme"] = theme
            return experiments
        except Exception as e:
            logger.error(f"Failed to generate experiments: {e}")
            # Fallback
            return [
                {
                    "theme": theme,
                    "variable": "scanner_breakout_confidence",
                    "baseline_value": "0.78",
                    "variant_value": "0.82",
                }
            ]

    async def run_experiment(self, exp: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Test a variant against the baseline using LLM for scoring."""
        prompt = prompts.EXPERIMENT_SCORER.format(
            variable=exp["variable"],
            variant=exp["variant_value"],
            baseline=exp["baseline_value"],
            context=context
        )
        try:
            raw = await self.llm.complete(prompt, json_response=True)
            res: Dict[str, Any] = json.loads(raw)
            return {
                "theme": exp["theme"],
                "variable": exp["variable"],
                "baseline_value": exp["baseline_value"],
                "variant_value": exp["variant_value"],
                **res
            }
        except Exception as e:
            logger.error(f"Failed to score experiment: {e}")
            # Fallback
            return {
                "theme": exp["theme"],
                "variable": exp["variable"],
                "baseline_value": exp["baseline_value"],
                "variant_value": exp["variant_value"],
                "score": 0.5,
                "delta_vs_baseline": 0.0,
                "metrics": {"error": True},
                "log": f"Error scoring: {e}"
            }

    async def compile_report(self, theme: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize findings into a daily proposal using LLM."""
        prompt = prompts.REPORT_COMPILER.format(theme=theme, results=json.dumps(results))
        try:
            raw = await self.llm.complete(prompt, json_response=True)
            report: Dict[str, Any] = json.loads(raw)
            # Add metadata
            report["theme"] = theme
            report["date"] = datetime.now(timezone.utc).isoformat()[:10]
            report["data_source"] = "swarm_history"
            report["full_data"] = {"results": results}
            return report
        except Exception as e:
            logger.error(f"Failed to compile report: {e}")
            winner = max(results, key=lambda x: x.get("delta_vs_baseline", 0)) if results else None
            return {
                "theme": theme,
                "date": datetime.now(timezone.utc).isoformat()[:10],
                "summary": f"Analyzed {len(results)} variants.",
                "recommendation": f"Adopt {winner['variable']}={winner['variant_value']}" if winner else "No recommendation",
                "regressions": "None",
                "safety_note": "Fallback report generated.",
                "full_data": {"results": results}
            }

    async def refine_strategies(self, history: str) -> None:
        """Read strategy files and propose optimizations via LLM."""
        strategy_dir = "strategies"
        if not os.path.exists(strategy_dir):
            logger.warning(f"Strategy directory {strategy_dir} not found.")
            return

        for filename in os.listdir(strategy_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                path = os.path.join(strategy_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        code = f.read()

                    prompt = prompts.STRATEGY_REFINERY.format(code=code, history=history)
                    raw = await self.llm.complete(prompt, json_response=True)
                    proposal: Dict[str, Any] = json.loads(raw)
                    
                    # Record the proposal as a strategy_refinement node in the DAG
                    self.dag.add_node(
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
                    logger.info(f"Generated refinement proposal for {filename}")
                except Exception as e:
                    logger.error(f"Failed to refine strategy {filename}: {e}")
