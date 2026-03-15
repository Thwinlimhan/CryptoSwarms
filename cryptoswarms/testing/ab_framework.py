"""A/B Testing Framework — route signals to strategy variants for comparison.

Enables safe testing of strategy improvements by splitting
signal traffic between control and test variants.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.testing.ab")


@dataclass
class Signal:
    """Signal representation for A/B routing."""
    symbol: str
    timestamp: str
    signal_type: str
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentConfig:
    """Configuration for an A/B experiment."""
    experiment_id: str
    variants: list[str]  # e.g., ["variant_a", "variant_b"]
    weights: list[float] | None = None  # Proportional weights
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class ExperimentResult:
    """Aggregated results for an experiment variant."""
    variant: str
    total_signals: int
    total_trades: int
    wins: int
    losses: int
    total_pnl: float
    avg_pnl_per_trade: float
    win_rate: float


class ABTestFramework:
    """A/B testing framework for strategy comparison.

    Routes signals to different strategy variants based on
    consistent hashing, ensuring the same symbol+timestamp
    always maps to the same variant.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentConfig] = {}
        self._assignment_counts: dict[str, dict[str, int]] = {}
        self._results: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def create_experiment(
        self,
        experiment_id: str,
        variants: list[str] | None = None,
        weights: list[float] | None = None,
    ) -> ExperimentConfig:
        """Create a new A/B experiment.

        Args:
            experiment_id: Unique experiment identifier.
            variants: List of variant names (default: ["variant_a", "variant_b"]).
            weights: Proportional weights for each variant.

        Returns:
            The created ExperimentConfig.
        """
        variants = variants or ["variant_a", "variant_b"]
        config = ExperimentConfig(
            experiment_id=experiment_id,
            variants=variants,
            weights=weights,
        )
        self._experiments[experiment_id] = config
        self._assignment_counts[experiment_id] = {v: 0 for v in variants}
        self._results[experiment_id] = {v: [] for v in variants}
        logger.info(
            "Experiment created: %s with variants %s", experiment_id, variants,
        )
        return config

    def assign_strategy_variant(
        self,
        signal: Signal | dict[str, Any],
        experiment_id: str = "default",
    ) -> str:
        """Assign a signal to a strategy variant.

        Uses consistent hashing so the same signal always gets
        the same variant assignment.

        Args:
            signal: The signal to route.
            experiment_id: Which experiment to use.

        Returns:
            The variant name (e.g., "variant_a").
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None or not experiment.is_active:
            return "variant_a"  # Default to control

        # Build hash key
        if isinstance(signal, dict):
            symbol = signal.get("symbol", "")
            timestamp = signal.get("timestamp", "")
        else:
            symbol = signal.symbol
            timestamp = signal.timestamp

        hash_input = f"{symbol}:{timestamp}:{experiment_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        variants = experiment.variants
        if experiment.weights and len(experiment.weights) == len(variants):
            # Weighted assignment
            total_weight = sum(experiment.weights)
            normalized = hash_val % int(total_weight * 1000)
            cumulative = 0.0
            for i, weight in enumerate(experiment.weights):
                cumulative += weight * 1000
                if normalized < cumulative:
                    variant = variants[i]
                    break
            else:
                variant = variants[-1]
        else:
            # Equal split
            variant = variants[hash_val % len(variants)]

        # Track assignment
        counts = self._assignment_counts.get(experiment_id, {})
        counts[variant] = counts.get(variant, 0) + 1

        return variant

    def record_outcome(
        self,
        experiment_id: str,
        variant: str,
        outcome: dict[str, Any],
    ) -> None:
        """Record the outcome of a trade in an experiment.

        Args:
            experiment_id: Which experiment.
            variant: Which variant produced the trade.
            outcome: Trade outcome data (should include 'pnl_usd' and 'win').
        """
        results = self._results.get(experiment_id, {})
        if variant in results:
            results[variant].append({
                **outcome,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })

    def get_experiment_results(
        self, experiment_id: str,
    ) -> dict[str, ExperimentResult]:
        """Get aggregated results for each variant in an experiment.

        Returns:
            Dict mapping variant name to ExperimentResult.
        """
        results = self._results.get(experiment_id, {})
        output: dict[str, ExperimentResult] = {}

        for variant, outcomes in results.items():
            total = len(outcomes)
            trades_with_pnl = [o for o in outcomes if "pnl_usd" in o]
            wins = sum(1 for o in trades_with_pnl if o.get("pnl_usd", 0) > 0)
            losses = len(trades_with_pnl) - wins
            total_pnl = sum(o.get("pnl_usd", 0) for o in trades_with_pnl)

            output[variant] = ExperimentResult(
                variant=variant,
                total_signals=self._assignment_counts.get(
                    experiment_id, {}
                ).get(variant, 0),
                total_trades=len(trades_with_pnl),
                wins=wins,
                losses=losses,
                total_pnl=round(total_pnl, 2),
                avg_pnl_per_trade=(
                    round(total_pnl / len(trades_with_pnl), 2)
                    if trades_with_pnl else 0.0
                ),
                win_rate=(
                    round(wins / len(trades_with_pnl), 4)
                    if trades_with_pnl else 0.0
                ),
            )

        return output

    def stop_experiment(self, experiment_id: str) -> None:
        """Stop an experiment."""
        experiment = self._experiments.get(experiment_id)
        if experiment:
            experiment.is_active = False
            logger.info("Experiment stopped: %s", experiment_id)

    def get_all_experiments(self) -> dict[str, dict[str, Any]]:
        """Return summary of all experiments."""
        return {
            eid: {
                "variants": exp.variants,
                "is_active": exp.is_active,
                "created_at": exp.created_at.isoformat(),
                "assignments": self._assignment_counts.get(eid, {}),
            }
            for eid, exp in self._experiments.items()
        }
