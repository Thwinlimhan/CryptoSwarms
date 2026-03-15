"""Strategy: Golden Cross (EMA 50 / 200).

A classic long-term trend indicator.
Triggers when the 50-period EMA crosses above the 200-period EMA.
"""

from __future__ import annotations

import logging
from typing import Any

from schemas.strategy import StrategyConfig
from cryptoswarms.common.strategy import BaseStrategy
from cryptoswarms.decision_engine import (
    BinaryDecisionInput, evaluate_binary_decision
)
from cryptoswarms.bayesian_update import bayes_update

logger = logging.getLogger("swarm.strategies.golden_cross")

CONFIG = StrategyConfig(
    id="strat-golden-cross",
    name="Golden Cross Trend",
    description="Captures major trend shifts using 50/200 EMA crossover.",
    universe=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    interval="4h",
    cooldown_cycles=48,
    confidence_threshold=0.85,
    parameters={
        "fast_period": 50,
        "slow_period": 200,
        "prior_baseline": 0.60,
        "take_profit_pct": 0.20,
        "trailing_stop_pct": 0.05
    },
    max_position_size_usd=10000.0,
    stop_loss_pct=0.04
)


class GoldenCrossStrategy(BaseStrategy):
    """The gold standard for long-term trend identification."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("signal_type") != "GOLDEN_CROSS":
            return None

        symbol = signal.get("symbol")
        
        # 1. Bayes Prior
        prior_prob = self.config.parameters.get("prior_baseline", 0.60)
        
        # 2. Evidence: Market Momentum (HTF)
        is_bull_regime = context.get("current_regime") == "BULLISH_TREND"
        likelihood_if_true = 0.85 if is_bull_regime else 0.5
        
        posterior = bayes_update(
            prior=prior_prob,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=0.25
        )

        # 3. EV Calculation
        decision_input = BinaryDecisionInput(
            prior_probability=posterior,
            likelihood_if_true=0.75,
            likelihood_if_false=0.25,
            payoff_win_usd=self.config.max_position_size_usd * 0.20,
            payoff_loss_usd=-(self.config.max_position_size_usd * self.config.stop_loss_pct),
            fees_usd=self.config.max_position_size_usd * 0.001
        )
        
        decision_result = evaluate_binary_decision(decision_input)

        if decision_result.positive_edge and decision_result.posterior_probability >= self.config.confidence_threshold:
            return {
                "strategy_id": self.config.id,
                "symbol": symbol,
                "action": "BUY",
                "confidence": decision_result.posterior_probability,
                "expected_value": decision_result.expected_value_after_costs_usd,
                "suggested_size_usd": self.config.max_position_size_usd,
                "metadata": {
                    "regime": context.get("current_regime"),
                    "type": "TREND_SHIFT"
                }
            }

        return None
