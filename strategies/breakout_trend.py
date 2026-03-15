"""Strategy: Volatility-Adjusted Breakout Trend."""

from __future__ import annotations

import logging
from typing import Any

from schemas.strategy import StrategyConfig
from cryptoswarms.common.strategy import BaseStrategy
from cryptoswarms.decision_engine import (
    BinaryDecisionInput, evaluate_binary_decision
)
from cryptoswarms.bayesian_update import bayes_update

logger = logging.getLogger("swarm.strategies.breakout")

CONFIG = StrategyConfig(
    id="strat-breakout-v1",
    name="Swarm Breakout Trend",
    description="Captures high-confidence breakouts using Bayesian confirmation.",
    universe=["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"],
    interval="15m",
    cooldown_cycles=6,
    confidence_threshold=0.8,
    parameters={
        "lookback_candles": 20,
        "std_dev_multiplier": 3.0,
        "prior_baseline": 0.45,  # Baseline probability of breakout success
        "smart_money_multiplier": 1.2, # Likelihood multiplier
        "regime_bonus": 0.15, # Additive bonus for trend regime
        "take_profit_pct": 0.08,
        "trailing_stop_pct": 0.025
    },
    max_position_size_usd=5000.0,
    stop_loss_pct=0.03
)


class BreakoutTrendStrategy(BaseStrategy):
    """Refined breakout strategy with Bayesian filtering."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Evaluate a breakout signal.
        Context should include:
          - regimes: list of recent regimes
          - smart_money: boolean or value
        """
        if signal.get("signal_type") != "BREAKOUT":
            return None

        symbol = signal.get("symbol")
        if self.config.universe and symbol not in self.config.universe:
            return None

        # 1. Start with Bayes Prior
        prior_prob = self.config.parameters.get("prior_baseline", 0.45)
        
        # 2. Evidence: Smart Money
        has_smart_money = context.get("smart_money", False)
        likelihood_if_true = 0.7 if has_smart_money else 0.5
        likelihood_if_false = 0.3 if has_smart_money else 0.5
        
        posterior = bayes_update(
            prior=prior_prob,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=likelihood_if_false
        )

        # 3. Evidence: Market Regime
        current_regime = context.get("current_regime", "UNKNOWN")
        if current_regime in ["BULLISH_TREND", "BEARISH_TREND"]:
            posterior += self.config.parameters.get("regime_bonus", 0.1)
        
        # 4. EV Calculation
        # Assume 2:1 Reward/Risk ratio for a standard breakout
        decision_input = BinaryDecisionInput(
            prior_probability=posterior,
            likelihood_if_true=0.6, # Likelihood of signal being correct
            likelihood_if_false=0.4,
            payoff_win_usd=self.config.max_position_size_usd * 0.04, # 4% target
            payoff_loss_usd=-(self.config.max_position_size_usd * self.config.stop_loss_pct),
            fees_usd=self.config.max_position_size_usd * 0.001 # 0.1% roundtrip
        )
        
        decision_result = evaluate_binary_decision(decision_input)

        if decision_result.positive_edge and decision_result.posterior_probability >= self.config.confidence_threshold:
            logger.info(f"STRATEGY TRIGGERED: {self.config.name} for {symbol} | EV: {decision_result.expected_value_after_costs_usd}")
            return {
                "strategy_id": self.config.id,
                "symbol": symbol,
                "action": "BUY", # Simplification: breakout implies buy
                "confidence": decision_result.posterior_probability,
                "expected_value": decision_result.expected_value_after_costs_usd,
                "suggested_size_usd": self.config.max_position_size_usd,
                "metadata": {
                    "regime": current_regime,
                    "smart_money": has_smart_money
                }
            }

        return None
