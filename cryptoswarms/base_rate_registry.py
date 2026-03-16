"""DEPRECATED: Legacy Base Rate Registry with fake data.

This module contains hardcoded, made-up base rates that have no statistical backing.
Use RealBaseRateRegistry instead for historically validated base rates.

MIGRATION PATH:
- Replace BaseRateRegistry with RealBaseRateRegistry
- Use AlphaDiscoveryEngine for real pattern validation
- Use EdgeQuantifier for real success rate calculations
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

# DEPRECATED: These are FAKE base rates with no statistical backing
@dataclass(frozen=True)
class LegacyBaseRateProfile:
    key: str
    success_rate: float
    sample_size: int
    source: str
    updated_at: datetime


class LegacyBaseRateRegistry:
    def __init__(self, profiles: list[LegacyBaseRateProfile] | None = None) -> None:
        self._profiles: dict[str, LegacyBaseRateProfile] = {}
        for profile in profiles or []:
            self.upsert(profile)

    def upsert(self, profile: LegacyBaseRateProfile) -> None:
        self._profiles[profile.key] = LegacyBaseRateProfile(
            key=profile.key,
            success_rate=_clamp_probability(profile.success_rate),
            sample_size=max(1, int(profile.sample_size)),
            source=profile.source,
            updated_at=profile.updated_at if profile.updated_at.tzinfo else profile.updated_at.replace(tzinfo=timezone.utc),
        )

    def get(self, key: str) -> LegacyBaseRateProfile | None:
        return self._profiles.get(key)

    def get_rate(self, key: str, *, default: float = 0.5) -> float:
        profile = self.get(key)
        if profile is None:
            return _clamp_probability(default)
        return profile.success_rate

    def empirical_bayes_prior(self, key: str, *, fallback: float = 0.5, pseudo_count: int = 20) -> float:
        profile = self.get(key)
        if profile is None:
            return _clamp_probability(fallback)

        base = _clamp_probability(fallback)
        observed = profile.success_rate
        n = max(1, profile.sample_size)
        k = max(1, int(pseudo_count))
        blended = (observed * n + base * k) / float(n + k)
        return _clamp_probability(blended)


# DEPRECATED: These are FAKE base rates - use RealBaseRateRegistry instead
DEFAULT_BASE_RATE_PROFILES: tuple[LegacyBaseRateProfile, ...] = (
    LegacyBaseRateProfile(
        key="phase1-btc-breakout-15m",
        success_rate=0.56,
        sample_size=200,
        source="internal-paper-ledger",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    LegacyBaseRateProfile(
        key="pairs-spread-mean-reversion",
        success_rate=0.54,
        sample_size=180,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    LegacyBaseRateProfile(
        key="volatility-compression-breakout",
        success_rate=0.53,
        sample_size=170,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    LegacyBaseRateProfile(
        key="cross-sectional-momentum-rotation",
        success_rate=0.55,
        sample_size=160,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
)


def default_base_rate_registry() -> LegacyBaseRateRegistry:
    return LegacyBaseRateRegistry(profiles=list(DEFAULT_BASE_RATE_PROFILES))


def _clamp_probability(value: float) -> float:
    return min(0.999, max(0.001, float(value)))
