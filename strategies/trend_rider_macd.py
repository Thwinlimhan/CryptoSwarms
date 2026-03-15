"""Strategy: Trend Rider MACD.

Follows strong momentum indicated by EMA crossovers and MACD histogram expansion.
Works best in trending regimes.
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

logger = logging.getLogger("swarm.strategies.trend_rider")

CONFIG = StrategyConfig(
    id="strat-trend-rider-macd",
    name="Trend Momentum Rider",
    description="Captures established trends using EMA 200 and MACD.",
    universe=["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT"],
    interval="1h",
    cooldown_cycles=24,
    confidence_threshold=0.82,
    parameters={
        "ema_fast": 12,
        "ema_slow": 26,
        "ema_base": 200,
        "prior_baseline": 0.50,
        "regime_trend_bonus": 0.25,
        "take_profit_pct": 0.10,
        "trailing_stop_pct": 0.04
    },
    max_position_size_usd=5000.0,
    stop_loss_pct=0.03
)


class TrendRiderMACDStrategy(BaseStrategy):
    """Rides broad market trends confirmed by momentum."""

    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        if signal.get("signal_type") not in ["TREND_CROSS", "MACD_BULLISH"]:
            return None

        symbol = signal.get("symbol")
        if self.config.universe and symbol not in self.config.universe:
            return None

        # 1. Bayes Prior
        prior_prob = self.config.parameters.get("prior_baseline", 0.50)
        
        # 2. Evidence: Higher Timeframe Alignment
        htf_bullish = context.get("htf_bullish", False) 
        likelihood_if_true = 0.75 if htf_bullish else 0.5
        
        posterior = bayes_update(
            prior=prior_prob,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=0.35
        )

        # 3. Evidence: Regime (Crucial for trend following)
        current_regime = context.get("current_regime", "UNKNOWN")
        if current_regime == "BULLISH_TREND":
            posterior += self.config.parameters.get("regime_trend_bonus", 0.25)
        elif current_regime == "RANGING":
            posterior -= 0.2 # Avoid getting chopped in a range
        
        # 4. EV Calculation (High target for long trends)
        decision_input = BinaryDecisionInput(
            prior_probability=posterior,
            likelihood_if_true=0.6,
            likelihood_if_false=0.4,
            payoff_win_usd=self.config.max_position_size_usd * 0.10,
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
                    "trend_type": "MOMENTUM_RIDER"
                }
            }

        return None
