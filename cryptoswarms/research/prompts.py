"""Prompts for the ResearchAgent - the 'Karpathy' loop for the swarm."""

EXPERIMENT_GENERATOR = """
Analyze the following swarm history (signals, decisions, and outcomes). 
Identify variables that could be optimized to improve PnL or accuracy.

HISTORY:
{history}

Goal: Propose 2-3 experiments. Each experiment should have:
- variable: name of the parameter (e.g., scanner_breakout_confidence)
- baseline: current value (estimated from history if not clear)
- variant: proposed new value
- hypothesis: why this might work

Return as JSON:
{{
  "theme": "performance_calibration",
  "experiments": [
    {{
      "variable": "...",
      "baseline_value": "...",
      "variant_value": "...",
      "hypothesis": "..."
    }}
  ]
}}
"""

EXPERIMENT_SCORER = """
Simulate/Score the following experiment variant against the historical context.
VARIABLE: {variable}
VARIANT: {variant}
BASELINE: {baseline}

CONTEXT:
{context}

Based on this historical data, how would this variant have performed?
Return a score (0.0 to 1.0) and a delta vs baseline score.

Return as JSON:
{{
  "score": 0.85,
  "delta_vs_baseline": 0.05,
  "metrics": {{
    "quality": 0.9,
    "latency": 0.1,
    "token_efficiency": 0.8
  }},
  "log": "Reasoning for the score..."
}}
"""

REPORT_COMPILER = """
Summarize the nightly research findings into a recommendation for the swarm.
THEME: {theme}
RESULTS: {results}

Provide:
- summary: Overall finding
- recommendation: Specific action to take
- regressions: Any risks identified

Return as JSON:
{{
  "summary": "...",
  "recommendation": "...",
  "regressions": "...",
  "safety_note": "..."
}}
"""

STRATEGY_REFINERY = """
Analyze the source code of the following strategy and the historical performance data.
Propose specific optimizations for the constants and parameters defined in the code.

STRATEGY CODE:
{code}

HISTORY:
{history}

Identify the best values for the 'parameters' dict in the StrategyConfig.
Return as JSON:
{{
  "strategy_id": "...",
  "proposed_parameters": {{
    "key": "value"
  }},
  "rationale": "...",
  "confidence": 0.0
}}
"""
