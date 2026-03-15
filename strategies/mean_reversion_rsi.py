"""Strategy: Mean Reversion RSI.

Triggers when price is oversold (RSI < 25) in a ranging or stabilizing market.
Uses Bayesian confirmation for trend exhaustion.
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

logger = logging.getLogger("swarm.strategies.mean_reversion")

CONFIG = StrategyConfig(
    id="strat-mean-reversion-rsi",
    name="Institutional Mean Reversion",
    description="Buys oversold RSI levels when regime is range-bound.",
    universe=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    interval="15m",
    cooldown_cycles=12,
    confidence_threshold=0.75,
    parameters={
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "prior_baseline": 0.45,
        "regime_range_bonus": 0.2,
        "take_profit_pct": 0.03,
        "trailing_stop_pct": 0.015
    },
    max_position_size_usd=3000.0,
    stop_loss_pct=0.02
)


class MeanReversionRSIStrategy(BaseStrategy):
    """Bounces off oversold levels in ranging markets."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("signal_type") not in ["RSI_OVERSOLD", "MEAN_REVERSION"]:
            return None

        symbol = signal.get("symbol")
        if self.config.universe and symbol not in self.config.universe:
            return None

        # 1. Bayes Prior
        prior_prob = self.config.parameters.get("prior_baseline", 0.40)
        
        # 2. Evidence: Smart Money (Contrarian)
        has_smart_money_buy = context.get("smart_money", False)
        likelihood_if_true = 0.65 if has_smart_money_buy else 0.5
        
        posterior = bayes_update(
            prior=prior_prob,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=0.45
        )

        # 3. Evidence: Regime (Prefer RANGING for reversion)
        current_regime = context.get("current_regime", "UNKNOWN")
        if current_regime in ["RANGING", "STABILIZING"]:
            posterior += self.config.parameters.get("regime_range_bonus", 0.2)
        elif current_regime == "BEARISH_TREND":
            posterior -= 0.1 # High risk of catching a falling knife
        
        # 4. EV Calculation
        decision_input = BinaryDecisionInput(
            prior_probability=posterior,
            likelihood_if_true=0.55,
            likelihood_if_false=0.45,
            payoff_win_usd=self.config.max_position_size_usd * 0.03,
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
                    "regime": current_regime,
                    "rsi_value": context.get("rsi_value"),
                    "type": "REVERSION"
                }
            }

        return None
