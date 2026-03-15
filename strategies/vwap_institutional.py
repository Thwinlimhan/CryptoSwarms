"""Strategy: Institutional VWAP Cross/Reversion.

Exploits Volume-Weighted Average Price (VWAP) deviations.
Institutional desks often target VWAP; retail deviations tend to snap back.
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

logger = logging.getLogger("swarm.strategies.vwap")

CONFIG = StrategyConfig(
    id="strat-vwap-institutional",
    name="Institutional VWAP Base",
    description="Targets price returns to day-VWAP after significant deviations.",
    universe=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    interval="5m",
    cooldown_cycles=60,
    confidence_threshold=0.88,
    parameters={
        "vwap_deviation_threshold": 0.02, # 2% deviation
        "prior_baseline": 0.55,
        "volume_surge_multiplier": 1.4,
        "take_profit_pct": 0.02,
        "trailing_stop_pct": 0.01
    },
    max_position_size_usd=10000.0,
    stop_loss_pct=0.015
)


class VWAPInstitutionalStrategy(BaseStrategy):
    """Execution-focused strategy based on volume-weighted prices."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("signal_type") not in ["VWAP_DEVIATION", "INSTITUTIONAL_SQUEEZE"]:
            return None

        symbol = signal.get("symbol")
        if self.config.universe and symbol not in self.config.universe:
            return None

        # 1. Bayes Prior
        prior_prob = self.config.parameters.get("prior_baseline", 0.55)
        
        # 2. Evidence: Volume Confirmation
        vol_surge = context.get("volume_surge", False)
        likelihood_if_true = 0.80 if vol_surge else 0.5
        
        posterior = bayes_update(
            prior=prior_prob,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=0.30
        )

        # 3. Evidence: Smart Money Clues
        smart_money = context.get("smart_money", False)
        if smart_money:
            posterior += 0.15 # Institutional activity confirmed
        
        # 4. EV Calculation
        decision_input = BinaryDecisionInput(
            prior_probability=posterior,
            likelihood_if_true=0.7,
            likelihood_if_false=0.3,
            payoff_win_usd=self.config.max_position_size_usd * 0.02,
            payoff_loss_usd=-(self.config.max_position_size_usd * self.config.stop_loss_pct),
            fees_usd=self.config.max_position_size_usd * 0.001
        )
        
        decision_result = evaluate_binary_decision(decision_input)

        if decision_result.positive_edge and decision_result.posterior_probability >= self.config.confidence_threshold:
            return {
                "strategy_id": self.config.id,
                "symbol": symbol,
                "action": "BUY" if signal.get("side") == "BELOW" else "SELL",
                "confidence": decision_result.posterior_probability,
                "expected_value": decision_result.expected_value_after_costs_usd,
                "suggested_size_usd": self.config.max_position_size_usd,
                "metadata": {
                    "vwap_price": context.get("vwap_price"),
                    "deviation": context.get("deviation_pct"),
                    "type": "INSTITUTIONAL"
                }
            }

        return None
