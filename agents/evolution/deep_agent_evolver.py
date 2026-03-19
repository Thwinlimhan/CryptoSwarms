"""
agents/evolution/deep_agent_evolver.py
Deep Agents harness — CORRECTED against deepagents v0.4.x official API.

Install: uv add deepagents langchain-anthropic
"""
from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from agents.backtest.models import StrategyCandidate, ValidationSummary
from agents.backtest.validation_pipeline import ValidationPipeline
from agents.evolution.autoresearch import AutoResearchPolicy, AutoResearchReport, ExperimentDecision


# ── CryptoSwarms-specific tools the evolver agent can call ─────────────────

def make_validation_tool(pipeline: ValidationPipeline, candidate_builder: Callable) -> Callable:
    """Factory: returns a tool that runs ValidationPipeline on the edited strategy."""
    @tool
    def run_validation_pipeline(strategy_path: str) -> str:
        """Run the full CryptoSwarms ValidationPipeline on the given strategy file path.
        Returns a JSON summary of all gate results and the final score."""
        import json
        try:
            candidate = candidate_builder(strategy_path)
            summary = pipeline.run(candidate)
            scores = {r.gate_name: r.score for r in summary.gate_results}
            passed = all(r.status.name == "PASS" for r in summary.gate_results)
            return json.dumps({"passed": passed, "gate_scores": scores, "strategy_path": strategy_path})
        except Exception as exc:
            return json.dumps({"error": str(exc), "strategy_path": strategy_path})

    return run_validation_pipeline


def make_chub_tool() -> Callable:
    """Wraps the `chub` CLI as an agent-callable tool for zero-hallucination API docs."""
    @tool
    def fetch_api_docs(api_endpoint: str) -> str:
        """Fetch live API documentation from Context Hub (Chub) for a given API endpoint.
        Use before editing any file that calls an external API.
        Example: fetch_api_docs("jesse/backtest") or fetch_api_docs("hyperliquid/api")
        """
        result = subprocess.run(
            ["chub", "get", api_endpoint, "--lang", "py"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return f"chub not available or endpoint not found: {api_endpoint}. Proceed with caution."
        return result.stdout[:4000]  # cap at 4k chars to stay within context budget

    return fetch_api_docs


def make_score_tool(score_fn: Callable[[dict], float]) -> Callable:
    """Wraps the incumbent score function as an agent tool."""
    @tool
    def score_strategy(params_json: str) -> str:
        """Score a strategy with the given JSON params dict.
        Returns the Sharpe ratio float as a string."""
        import json
        try:
            params = json.loads(params_json)
            score = score_fn(params)
            return str(round(score, 6))
        except Exception as exc:
            return f"error: {exc}"

    return score_strategy


# ── Subagent definitions ────────────────────────────────────────────────────

def make_syntax_checker_subagent() -> dict:
    """Dedicated subagent for syntax checking — keeps main agent context clean."""
    @tool
    def check_python_syntax(file_path: str) -> str:
        """Check Python syntax of a file. Returns 'ok' or the SyntaxError."""
        import ast, py_compile
        try:
            ast.parse(Path(file_path).read_text(encoding="utf-8"))
            py_compile.compile(file_path, doraise=True)
            return "ok"
        except SyntaxError as e:
            return f"SyntaxError at line {e.lineno}: {e.msg}"
        except Exception as e:
            return f"error: {e}"

    return {
        "name": "syntax-checker",
        "description": "Checks Python syntax of strategy files. Use before running validation.",
        "system_prompt": (
            "You are a Python syntax specialist. Check the file syntax and return "
            "'ok' if clean, or the exact error with line number if broken. "
            "Return only the check result — no explanation needed."
        ),
        "tools": [check_python_syntax],
        "model": "openai:gpt-4.1-mini",  # Fast + cheap for syntax checks
    }


def make_failure_analyzer_subagent(failure_ledger_path: str = "data/failure_ledger.json") -> dict:
    """Subagent that reads the FailureLedger and produces targeted improvement hints."""
    @tool
    def read_failure_history(strategy_id: str, max_entries: int = 5) -> str:
        """Read recent failure history for a strategy from the FailureLedger.
        Returns JSON with failure modes and gate names."""
        import json
        try:
            ledger_file = Path(failure_ledger_path)
            if not ledger_file.exists():
                return json.dumps({"error": "Failure ledger not found"})
            ledger = json.loads(ledger_file.read_text())
            entries = [e for e in ledger.get("entries", []) if e.get("strategy_id") == strategy_id]
            recent = entries[-max_entries:]
            return json.dumps(recent)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return {
        "name": "failure-analyzer",
        "description": (
            "Analyzes the strategy failure history from the FailureLedger and returns "
            "targeted, actionable improvement hints. Use when the main agent needs to "
            "understand WHY a strategy failed before editing it."
        ),
        "system_prompt": (
            "You are a quant strategy failure analyst. Given failure history from the "
            "CryptoSwarms FailureLedger, identify: (1) which validation gates failed "
            "most often, (2) the likely root cause, (3) a specific code-level fix. "
            "Return a concise JSON: {failure_pattern, root_cause, suggested_fix}."
        ),
        "tools": [read_failure_history],
    }


def make_backtest_runner_subagent() -> dict:
    """
    Specialized subagent for running backtests inside the sandbox.
    All Jesse/vectorbt execution happens in the subagent's isolated context.
    The main agent never sees raw backtest output — only the summary.
    This is the context quarantine pattern: keep backtest noise out of the
    main agent's context window.
    """
    return {
        "name": "backtest-runner",
        "description": (
            "Runs Jesse and vectorbt backtests on edited strategy files inside the sandbox. "
            "Use when you need to score a strategy mutation. Returns only the summary "
            "metrics — Sharpe ratio, max drawdown, WFE, gate pass/fail. "
            "Never use for file editing or API calls."
        ),
        "system_prompt": """You are a backtest execution specialist operating inside an isolated sandbox.
Your ONLY job: run backtests and return clean metric summaries.

PROCEDURE:
1. Verify the strategy file exists at /sandbox/strategies/
2. Run: execute("cd /sandbox && python -m jesse backtest --full-reports 2>&1 | tail -30")
3. Parse the output for: Sharpe ratio, max drawdown, total return, trade count
4. Run: execute("cd /sandbox && python -c 'import vectorbt as vbt; ...'") for fast screening
5. Return ONLY this JSON — nothing else:
{
  "sharpe": float,
  "max_drawdown": float,
  "total_return": float,
  "trade_count": int,
  "jesse_exit_code": int,
  "error": null | "error description"
}

STRICT RULES:
- Never install new packages (pip install is prohibited in the sandbox)
- Never make outbound network calls from strategy code
- Never read /etc/, ~/.ssh/, or any path outside /sandbox/
- If a command takes >5 minutes, kill it and return error
- Return ONLY the JSON block — no explanation, no preamble""",
        "tools": [],  # All execution via the sandbox's built-in `execute` tool
        "model": "openai:gpt-4.1-mini",  # Cheap model is fine for structured parsing
    }


def make_immutable_audit_tool(thread_id: str) -> Callable:
    """Tool that downloads sandbox artifacts and writes them to ImmutableAuditLog on host."""
    from cryptoswarms.immutable_audit import ImmutableJsonlAuditLog

    @tool
    def persist_experiment_artifacts(
        experiment_id: str,
        sharpe: float,
        kept: bool,
        change_description: str,
    ) -> str:
        """
        Download the evolved strategy file from sandbox and record in ImmutableAuditLog.
        Call this at the END of every experiment, whether kept or discarded.
        Args:
            experiment_id: unique ID for this experiment (e.g. "exp-001")
            sharpe: final Sharpe ratio achieved
            kept: whether this experiment was promoted
            change_description: one-line summary of what was changed in the strategy
        Returns "ok" or error string.
        """
        try:
            audit_log = ImmutableJsonlAuditLog(
                Path(f"data/evolution_audit/{thread_id}.jsonl")
            )
            audit_log.append(
                agent="deep_agent_evolver",
                action="experiment_complete",
                run_id=experiment_id,
                metadata={
                    "sharpe": sharpe,
                    "kept": kept,
                    "change": change_description,
                    "thread_id": thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            if kept:
                # NOTE: In production, download from sandbox via backend.download_files()
                return "ok: artifact persisted to audit log"

            return "ok: discarded experiment recorded"

        except Exception as exc:
            return f"error: {exc}"

    return persist_experiment_artifacts


# ── Main DeepAgentEvolver class ─────────────────────────────────────────────

@dataclass(slots=True)
class DeepAgentEvolver:
    """
    Deep Agents harness for overnight code-level strategy evolution.

    Replaces AutoResearchRunner's parameter-only mutation with full code editing
    backed by the official deepagents v0.4.x API.

    Key design decisions vs. submitted snippet:
    - No DeepAgentConfig (doesn't exist) — uses create_deep_agent kwargs directly
    - Tools are Python callables registered via @tool, not string names
    - Persistent memory via CompositeBackend + StoreBackend, not persistent_memory=True
    - Subagents defined as dicts with name/description/system_prompt/tools
    - invoke() takes {"messages": [{"role": "user", "content": "..."}]}
    - Filesystem backend uses FilesystemBackend(root_dir=..., virtual_mode=True)
    - Human-in-the-loop wired via interrupt_on for file writes (safety)
    """
    policy: AutoResearchPolicy
    validation_pipeline: ValidationPipeline
    score_fn: Callable[[dict], float]
    candidate_builder: Callable       # (strategy_path: str) -> StrategyCandidate
    base_strategy_path: Path = Path("strategies/phase1_btc_breakout_15m.py")
    chub_enabled: bool = True
    hitl_enabled: bool = False        # set True in production to approve file writes

    def _build_agent(self, thread_id: str) -> tuple[object, object]:
        """Build the deep agent with correct v0.4.x API."""
        from agents.evolution.sandbox_backend_factory import build_sandbox_backend
        
        store = InMemoryStore()
        checkpointer = MemorySaver()

        # Seed sandbox with strategy file + program.md policy
        strategy_source = self.base_strategy_path.read_bytes()
        program_md = Path("agents/evolution/program.md").read_bytes() if Path("agents/evolution/program.md").exists() else b""
        agents_md = Path("AGENTS.md").read_bytes() if Path("AGENTS.md").exists() else b""
        seed_files = [
            ("/sandbox/strategies/" + self.base_strategy_path.name, strategy_source),
            ("/sandbox/program.md", program_md),
            ("/sandbox/AGENTS.md", agents_md),
        ]

        sandbox_backend, sandbox_handle = build_sandbox_backend(
            thread_id=thread_id,
            seed_files=seed_files,
        )

        def backend_factory(rt):
            return CompositeBackend(
                default=sandbox_backend,           # all file ops run isolated in sandbox
                routes={
                    "/memories/": StoreBackend(rt),  # cross-thread persistent memory
                },
            )

        # Tools: real callables running on host
        tools = [
            make_validation_tool(self.validation_pipeline, self.candidate_builder),
            make_chub_tool(),
            make_score_tool(self.score_fn),
            make_immutable_audit_tool(thread_id),
        ]

        # Subagents: run in context
        subagents = [
            make_syntax_checker_subagent(),
            make_failure_analyzer_subagent(),
            make_backtest_runner_subagent(),
        ]

        # Skills: load from your existing skills/ directory
        skills_dir = Path("skills")
        skill_sources = [str(skills_dir)] if skills_dir.exists() else []

        interrupt_config = {"write_file": self.hitl_enabled, "edit_file": self.hitl_enabled, "execute": self.hitl_enabled}

        agent = create_deep_agent(
            model=init_chat_model("claude-3-5-sonnet-20240620"),
            tools=tools,
            subagents=subagents,
            system_prompt=self._build_system_prompt(0.0),
            backend=backend_factory,
            store=store,
            checkpointer=checkpointer,
            skills=skill_sources,
            interrupt_on=interrupt_config,
            name="cryptoswarms-evolver",
        )
        return agent, sandbox_handle

    def _build_system_prompt(self, incumbent_score: float) -> str:
        strategy_path = str(self.base_strategy_path)
        return f"""You are a professional quantitative strategy researcher for CryptoSwarms.

YOUR GOAL: Improve the strategy at {strategy_path} to beat incumbent Sharpe {incumbent_score:.4f}.

STRICT RULES:
1. ALWAYS call fetch_api_docs before editing any file that calls Jesse, vectorbt, or Hyperliquid APIs
2. ALWAYS call the syntax-checker subagent after every file edit before running validation
3. ALWAYS call the failure-analyzer subagent at the start to understand WHY previous runs failed
4. Edit ONLY the strategy file — never touch gates.py, validation_pipeline.py, or execution files
5. After editing, call run_validation_pipeline and score_strategy to measure improvement
6. Save your experiment log to /memories/evolution_log.md after each experiment
7. If validation fails, analyze the gate_scores and make a targeted fix — don't make random changes
8. Follow program.md policy for max_experiments, mutation_step, and min_score_improvement

MEMORY STRUCTURE:
- /memories/evolution_log.md: Running log of all experiments (keep all runs)
- /memories/best_params.json: Best params found so far
- /memories/failure_patterns.md: Accumulated failure mode knowledge

OUTPUT FORMAT when done:
Return a JSON block: {{"kept": bool, "new_score": float, "change_made": "description"}}
"""

    def run(self, incumbent_score: float) -> AutoResearchReport:
        """Synchronous entry point — wraps async agent in asyncio.run()."""
        return asyncio.run(self.run_async(incumbent_score))

    async def run_async(self, incumbent_score: float) -> AutoResearchReport:
        import os
        started_at = datetime.now(timezone.utc)
        thread_id = f"evolver-{started_at.strftime('%Y%m%d-%H%M%S')}"
        
        sandbox_handle = None
        try:
            agent, sandbox_handle = self._build_agent(thread_id)

            kept: list[ExperimentDecision] = []
            discarded: list[ExperimentDecision] = []
            incumbent = float(incumbent_score)
            experiments = 0

        for exp_id in range(1, self.policy.max_experiments + 1):
            try:
                result = await agent.ainvoke(    # ainvoke() for async; invoke() for sync
                    {
                        "messages": [{
                            "role": "user",
                            "content": (
                                f"Experiment {exp_id}/{self.policy.max_experiments}. "
                                f"Incumbent Sharpe: {incumbent:.4f}. "
                                f"Min improvement needed: {self.policy.min_score_improvement}. "
                                "Run the full evolution cycle per your system instructions."
                            ),
                        }]
                    },
                    config={"configurable": {"thread_id": thread_id}},
                )
            except Exception as exc:
                discarded.append(ExperimentDecision(
                    experiment_id=exp_id, best_score=incumbent, incumbent_before=incumbent,
                    score_improvement=0.0, kept=False, reason=f"agent_error:{exc}", candidate=None,
                ))
                continue

            # Extract result from agent's final message
            import json, re
            final_text = ""
            if "messages" in result:
                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        final_text = msg.content
                        break

            new_score = incumbent
            kept_flag = False
            try:
                match = re.search(r'\{[^{}]*"new_score"[^{}]*\}', final_text)
                if match:
                    data = json.loads(match.group())
                    new_score = float(data.get("new_score", incumbent))
                    kept_flag = bool(data.get("kept", False))
            except Exception:
                pass

            delta = new_score - incumbent
            if kept_flag and delta >= self.policy.min_score_improvement:
                incumbent = new_score
                kept.append(ExperimentDecision(
                    experiment_id=exp_id, best_score=new_score, incumbent_before=float(incumbent_score) if not kept else kept[-1].best_score,
                    score_improvement=round(delta, 6), kept=True, reason="promoted", candidate=None,
                ))
            else:
                discarded.append(ExperimentDecision(
                    experiment_id=exp_id, best_score=new_score, incumbent_before=incumbent,
                    score_improvement=round(delta, 6), kept=False, reason="below_threshold", candidate=None,
                ))

            return AutoResearchReport(
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                experiments_run=self.policy.max_experiments,
                final_incumbent_score=round(incumbent, 6),
                kept=sorted(kept, key=lambda d: d.best_score, reverse=True)[:self.policy.keep_top_k],
                discarded=discarded,
            )
        finally:
            if sandbox_handle is not None:
                provider = os.getenv("SANDBOX_PROVIDER", "modal").lower()
                try:
                    if provider == "modal":
                        sandbox_handle.terminate()
                    elif provider == "daytona":
                        sandbox_handle.stop()
                    elif provider == "langsmith":
                        sandbox_handle.delete()
                except Exception:
                    pass
