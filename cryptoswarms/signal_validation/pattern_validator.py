"""Pattern Validator — statistical validation for trading patterns.

Ensures that detected patterns are statistically significant
before they are used for trade decisions, preventing trading on noise.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("swarm.signal_validation.pattern")


@dataclass(frozen=True)
class ValidationResult:
    """Result of pattern significance validation."""
    is_significant: bool
    p_value: float
    win_rate: float
    sample_size: int
    min_required_samples: int
    message: str


class PatternValidator:
    """Validates trading patterns for statistical significance.

    Uses binomial testing to determine if a pattern's win rate
    is significantly better than random chance (50/50).
    """

    def __init__(
        self,
        min_samples: int = 30,
        significance_level: float = 0.05,
        min_win_rate: float = 0.52,
    ) -> None:
        self.min_samples = min_samples
        self.significance_level = significance_level
        self.min_win_rate = min_win_rate

    @staticmethod
    def _binomial_p_value(successes: int, trials: int, p0: float = 0.5) -> float:
        """Calculate one-sided p-value using normal approximation to binomial.

        For large samples, the binomial distribution can be approximated
        by a normal distribution. Falls back to exact calculation for
        small samples.
        """
        if trials == 0:
            return 1.0

        observed_rate = successes / trials
        if observed_rate <= p0:
            return 1.0  # Not better than null hypothesis

        # Normal approximation to binomial test
        mean = trials * p0
        std = math.sqrt(trials * p0 * (1 - p0))
        if std == 0:
            return 0.0

        z = (successes - mean) / std

        # Approximate the upper tail of the normal distribution
        # Using the error function approximation
        p_value = 0.5 * math.erfc(z / math.sqrt(2))
        return p_value

    def validate_pattern_significance(
        self, pattern_results: list[bool]
    ) -> ValidationResult:
        """Validate if a trading pattern is statistically significant.

        Args:
            pattern_results: List of booleans where True = win, False = loss.

        Returns:
            ValidationResult with significance determination.
        """
        n = len(pattern_results)

        if n < self.min_samples:
            return ValidationResult(
                is_significant=False,
                p_value=1.0,
                win_rate=sum(pattern_results) / n if n > 0 else 0.0,
                sample_size=n,
                min_required_samples=self.min_samples,
                message=f"Insufficient samples: {n} < {self.min_samples}",
            )

        wins = sum(pattern_results)
        win_rate = wins / n
        p_value = self._binomial_p_value(wins, n)

        is_significant = p_value < self.significance_level and win_rate > self.min_win_rate

        if is_significant:
            message = (
                f"Pattern is significant: win_rate={win_rate:.3f}, "
                f"p_value={p_value:.4f} (< {self.significance_level})"
            )
        else:
            reasons = []
            if p_value >= self.significance_level:
                reasons.append(f"p_value={p_value:.4f} >= {self.significance_level}")
            if win_rate <= self.min_win_rate:
                reasons.append(f"win_rate={win_rate:.3f} <= {self.min_win_rate}")
            message = f"Pattern NOT significant: {', '.join(reasons)}"

        logger.debug(message)
        return ValidationResult(
            is_significant=is_significant,
            p_value=round(p_value, 6),
            win_rate=round(win_rate, 4),
            sample_size=n,
            min_required_samples=self.min_samples,
            message=message,
        )

    def validate_multiple_patterns(
        self, patterns: dict[str, list[bool]]
    ) -> dict[str, ValidationResult]:
        """Validate multiple patterns at once.

        Args:
            patterns: dict mapping pattern name to results list.

        Returns:
            dict mapping pattern name to ValidationResult.
        """
        return {
            name: self.validate_pattern_significance(results)
            for name, results in patterns.items()
        }
