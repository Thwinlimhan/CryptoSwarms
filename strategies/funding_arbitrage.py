"""Strategy: Funding Arbitrage / Squeeze."""

from __future__ import annotations

import logging
from typing import Any

from schemas.strategy import StrategyConfig
from cryptoswarms.common.strategy import BaseStrategy
from cryptoswarms.decision_engine import (
    BinaryDecisionInput, evaluate_binary_decision
)

logger = logging.getLogger("swarm.strategies.funding")

CONFIG = StrategyConfig(
    id="strat-funding-v1",
    name="Funding Arbitrage Sweep",
    description="Captures收益 (yield) from extreme funding rates and squeeze potential.",
    universe=[], # Global
    interval="8h",
    cooldown_cycles=3,
    confidence_threshold=0.65,
    parameters={
        "min_funding_rate": 0.0005, # 0.05% per 8h
        "squeeze_prior": 0.3,
        "whale_inflow_bonus": 0.2,
        "take_profit_pct": 0.03
    },
    stop_loss_pct=0.015
)


class FundingArbitrageStrategy(BaseStrategy):
    """Monitors for funding imbalances to take mean reversion or yield positions."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("signal_type") not in ["FUNDING_HIGH", "FUNDING_LOW", "FUNDING_EXTREME"]:
            return None

        symbol = signal.get("symbol")
        funding_rate = signal.get("confidence", 0) # Assuming confidence field carries the rate or a score
        
        # 1. Evaluate Squeeze Opportunity
        # If funding is LOW (Negative), it's a SHORT squeeze opportunity.
        is_short_squeeze = signal.get("signal_type") == "FUNDING_LOW"
        
        prior = self.config.parameters.get("squeeze_prior", 0.3)
        if context.get("smart_money", False):
            prior += self.config.parameters.get("whale_inflow_bonus", 0.2)
            
        decision_input = BinaryDecisionInput(
            prior_probability=prior,
            likelihood_if_true=0.7,
            likelihood_if_false=0.3,
            payoff_win_usd=100.0, # Placeholder
            payoff_loss_usd=-50.0,
            fees_usd=5.0
        )
        
        res = evaluate_binary_decision(decision_input)
        
        if res.positive_edge:
            return {
                "strategy_id": self.config.id,
                "symbol": symbol,
                "action": "LONG" if is_short_squeeze else "SHORT",
                "confidence": res.posterior_probability,
                "expected_value": res.expected_value_after_costs_usd,
                "metadata": {
                    "funding_skew": "NEGATIVE" if is_short_squeeze else "POSITIVE",
                    "type": "SQUEEZE_PLAY"
                }
            }
            
        return None
