"""Real Base Rate Registry for CryptoSwarms.

Replaces fake base rates with real historical validation from backtesting.
All base rates are calculated from actual historical performance data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger("cryptoswarms.real_base_rates")

@dataclass(frozen=True)
class RealBaseRateProfile:
    """Real base rate profile calculated from historical data."""
    key: str
    success_rate: float
    sample_size: int
    source: str
    updated_at: datetime
    
    # Additional real metrics (not available in fake version)
    expected_return_per_trade: float
    sharpe_ratio: float
    max_drawdown: float
    statistical_significance: float  # p-value
    confidence_interval: tuple[float, float]
    regime_breakdown: Dict[str, float]
    transaction_cost_impact: float

@dataclass
class BaseRateValidationResult:
    """Result of base rate validation."""
    is_valid: bool
    confidence_score: float
    sample_adequacy: bool
    statistical_significance: bool
    economic_significance: bool
    issues: List[str]

class RealBaseRateRegistry:
    """Registry for real, historically validated base rates."""
    
    def __init__(self, alpha_discovery_engine=None):
        self.alpha_engine = alpha_discovery_engine
        self._profiles: Dict[str, RealBaseRateProfile] = {}
        self._last_update: Optional[datetime] = None
        
    def calculate_real_base_rates(
        self, 
        pattern_id: str, 
        symbol: str, 
        interval: str = "15m",
        lookback_days: int = 365
    ) -> RealBaseRateProfile:
        """Calculate REAL base rates from historical backtesting."""
        
        if not self.alpha_engine:
            raise ValueError("AlphaDiscoveryEngine required for real base rate calculation")
        
        logger.info(f"Calculating real base rates for {pattern_id} on {symbol}")
        
        # Get deployed pattern
        deployed_pattern = self.alpha_engine.get_pattern_for_trading(symbol, interval, pattern_id)
        
        if not deployed_pattern:
            raise ValueError(f"No deployed pattern found for {pattern_id} on {symbol}")
        
        edge_metrics = deployed_pattern.edge_metrics
        
        # Calculate regime breakdown
        regime_breakdown = {}
        for regime_name, regime_metrics in edge_metrics.regime_performance.items():
            regime_breakdown[regime_name] = regime_metrics.expected_return
        
        # Create real base rate profile
        profile = RealBaseRateProfile(
            key=f"{pattern_id}-{symbol}-{interval}",
            success_rate=edge_metrics.win_rate,
            sample_size=edge_metrics.sample_size,
            source="real-historical-backtest",
            updated_at=datetime.now(timezone.utc),
            expected_return_per_trade=edge_metrics.expected_return_per_trade,
            sharpe_ratio=edge_metrics.sharpe_ratio,
            max_drawdown=edge_metrics.max_drawdown,
            statistical_significance=edge_metrics.p_value,
            confidence_interval=edge_metrics.confidence_interval,
            regime_breakdown=regime_breakdown,
            transaction_cost_impact=edge_metrics.transaction_cost_impact
        )
        
        # Store in registry
        self.upsert(profile)
        
        logger.info(f"✅ Real base rate calculated: {edge_metrics.win_rate:.1%} success rate "
                   f"({edge_metrics.sample_size} trades, p={edge_metrics.p_value:.4f})")
        
        return profile
    
    def upsert(self, profile: RealBaseRateProfile) -> None:
        """Store or update a real base rate profile."""
        
        # Validate profile before storing
        validation = self._validate_profile(profile)
        
        if not validation.is_valid:
            logger.warning(f"Base rate profile validation failed: {', '.join(validation.issues)}")
            # Store anyway but with warning
        
        self._profiles[profile.key] = profile
        self._last_update = datetime.now(timezone.utc)
        
        logger.info(f"Stored real base rate: {profile.key} "
                   f"(success_rate={profile.success_rate:.1%}, "
                   f"sample_size={profile.sample_size})")
    
    def get(self, key: str) -> Optional[RealBaseRateProfile]:
        """Get a real base rate profile."""
        return self._profiles.get(key)
    
    def get_rate(self, key: str, *, default: float = 0.5) -> float:
        """Get success rate with fallback."""
        profile = self.get(key)
        if profile is None:
            logger.warning(f"No real base rate found for {key}, using default {default}")
            return _clamp_probability(default)
        return profile.success_rate
    
    def get_expected_return(self, key: str, *, default: float = 0.0) -> float:
        """Get expected return per trade."""
        profile = self.get(key)
        if profile is None:
            return default
        return profile.expected_return_per_trade
    
    def get_sharpe_ratio(self, key: str, *, default: float = 0.0) -> float:
        """Get Sharpe ratio."""
        profile = self.get(key)
        if profile is None:
            return default
        return profile.sharpe_ratio
    
    def is_statistically_significant(self, key: str, alpha: float = 0.05) -> bool:
        """Check if base rate is statistically significant."""
        profile = self.get(key)
        if profile is None:
            return False
        return profile.statistical_significance < alpha
    
    def is_economically_significant(self, key: str, min_return: float = 0.01) -> bool:
        """Check if base rate represents economic significance."""
        profile = self.get(key)
        if profile is None:
            return False
        return profile.expected_return_per_trade > min_return
    
    def get_regime_performance(self, key: str, regime: str) -> Optional[float]:
        """Get performance for specific market regime."""
        profile = self.get(key)
        if profile is None:
            return None
        return profile.regime_breakdown.get(regime)
    
    def empirical_bayes_prior(
        self, 
        key: str, 
        *, 
        fallback: float = 0.5, 
        pseudo_count: int = 20
    ) -> float:
        """Calculate empirical Bayes prior with real data."""
        
        profile = self.get(key)
        if profile is None:
            logger.warning(f"No real base rate for {key}, using fallback")
            return _clamp_probability(fallback)
        
        # Use real sample size and success rate
        base = _clamp_probability(fallback)
        observed = profile.success_rate
        n = max(1, profile.sample_size)
        k = max(1, int(pseudo_count))
        
        # Weight by statistical significance
        significance_weight = 1.0 - profile.statistical_significance  # Lower p-value = higher weight
        significance_weight = max(0.1, min(1.0, significance_weight))
        
        blended = (observed * n * significance_weight + base * k) / float(n * significance_weight + k)
        return _clamp_probability(blended)
    
    def refresh_all_base_rates(self, max_age_days: int = 30):
        """Refresh base rates older than max_age_days."""
        
        if not self.alpha_engine:
            logger.warning("Cannot refresh base rates without AlphaDiscoveryEngine")
            return
        
        current_time = datetime.now(timezone.utc)
        profiles_to_refresh = []
        
        for key, profile in self._profiles.items():
            age = (current_time - profile.updated_at).days
            if age > max_age_days:
                profiles_to_refresh.append(key)
        
        if profiles_to_refresh:
            logger.info(f"Refreshing {len(profiles_to_refresh)} old base rates")
            
            for key in profiles_to_refresh:
                try:
                    # Parse key to extract pattern info
                    parts = key.split('-')
                    if len(parts) >= 3:
                        pattern_id = parts[0]
                        symbol = parts[1]
                        interval = parts[2]
                        
                        # Recalculate base rate
                        self.calculate_real_base_rates(pattern_id, symbol, interval)
                        
                except Exception as e:
                    logger.error(f"Error refreshing base rate {key}: {e}")
    
    def get_all_profiles(self) -> List[RealBaseRateProfile]:
        """Get all real base rate profiles."""
        return list(self._profiles.values())
    
    def get_summary_stats(self) -> Dict[str, float]:
        """Get summary statistics across all base rates."""
        
        if not self._profiles:
            return {"status": "No real base rates available"}
        
        profiles = list(self._profiles.values())
        
        return {
            "total_profiles": len(profiles),
            "avg_success_rate": sum(p.success_rate for p in profiles) / len(profiles),
            "avg_expected_return": sum(p.expected_return_per_trade for p in profiles) / len(profiles),
            "avg_sharpe_ratio": sum(p.sharpe_ratio for p in profiles) / len(profiles),
            "avg_sample_size": sum(p.sample_size for p in profiles) / len(profiles),
            "statistically_significant_count": sum(1 for p in profiles if p.statistical_significance < 0.05),
            "economically_significant_count": sum(1 for p in profiles if p.expected_return_per_trade > 0.01),
            "avg_transaction_cost_impact": sum(p.transaction_cost_impact for p in profiles) / len(profiles)
        }
    
    def _validate_profile(self, profile: RealBaseRateProfile) -> BaseRateValidationResult:
        """Validate a base rate profile."""
        
        issues = []
        
        # Sample size adequacy
        sample_adequacy = profile.sample_size >= 100
        if not sample_adequacy:
            issues.append(f"Small sample size: {profile.sample_size} < 100")
        
        # Statistical significance
        statistical_significance = profile.statistical_significance < 0.05
        if not statistical_significance:
            issues.append(f"Not statistically significant: p={profile.statistical_significance:.4f}")
        
        # Economic significance
        economic_significance = profile.expected_return_per_trade > 0.005  # >0.5% per trade
        if not economic_significance:
            issues.append(f"Low expected return: {profile.expected_return_per_trade:.2%}")
        
        # Success rate sanity check
        if profile.success_rate < 0.3 or profile.success_rate > 0.9:
            issues.append(f"Unusual success rate: {profile.success_rate:.1%}")
        
        # Transaction cost impact
        if profile.transaction_cost_impact > 0.5:  # >50% of gross returns
            issues.append(f"High transaction cost impact: {profile.transaction_cost_impact:.1%}")
        
        confidence_score = 1.0
        if issues:
            confidence_score = max(0.1, 1.0 - len(issues) * 0.2)
        
        return BaseRateValidationResult(
            is_valid=len(issues) == 0,
            confidence_score=confidence_score,
            sample_adequacy=sample_adequacy,
            statistical_significance=statistical_significance,
            economic_significance=economic_significance,
            issues=issues
        )

def default_real_base_rate_registry(alpha_discovery_engine=None) -> RealBaseRateRegistry:
    """Create default real base rate registry."""
    return RealBaseRateRegistry(alpha_discovery_engine)

def _clamp_probability(value: float) -> float:
    """Clamp probability to valid range."""
    return min(0.999, max(0.001, float(value)))