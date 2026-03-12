from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BaseRateProfile:
    key: str
    success_rate: float
    sample_size: int
    source: str
    updated_at: datetime


class BaseRateRegistry:
    def __init__(self, profiles: list[BaseRateProfile] | None = None) -> None:
        self._profiles: dict[str, BaseRateProfile] = {}
        for profile in profiles or []:
            self.upsert(profile)

    def upsert(self, profile: BaseRateProfile) -> None:
        self._profiles[profile.key] = BaseRateProfile(
            key=profile.key,
            success_rate=_clamp_probability(profile.success_rate),
            sample_size=max(1, int(profile.sample_size)),
            source=profile.source,
            updated_at=profile.updated_at if profile.updated_at.tzinfo else profile.updated_at.replace(tzinfo=timezone.utc),
        )

    def get(self, key: str) -> BaseRateProfile | None:
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


DEFAULT_BASE_RATE_PROFILES: tuple[BaseRateProfile, ...] = (
    BaseRateProfile(
        key="phase1-btc-breakout-15m",
        success_rate=0.56,
        sample_size=200,
        source="internal-paper-ledger",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    BaseRateProfile(
        key="pairs-spread-mean-reversion",
        success_rate=0.54,
        sample_size=180,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    BaseRateProfile(
        key="volatility-compression-breakout",
        success_rate=0.53,
        sample_size=170,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
    BaseRateProfile(
        key="cross-sectional-momentum-rotation",
        success_rate=0.55,
        sample_size=160,
        source="internal-backtests",
        updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    ),
)


def default_base_rate_registry() -> BaseRateRegistry:
    return BaseRateRegistry(profiles=list(DEFAULT_BASE_RATE_PROFILES))


def _clamp_probability(value: float) -> float:
    return min(0.999, max(0.001, float(value)))
