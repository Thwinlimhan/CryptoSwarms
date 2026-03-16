"""Alpha Discovery Engine - Main Integration Layer.

Orchestrates the complete pipeline from historical data to validated patterns.
Replaces the fake backtesting and hardcoded parameters with real alpha discovery.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from cryptoswarms.data.historical_engine import HistoricalDataEngine, MarketRegimeClassifier
from cryptoswarms.patterns.discovery_engine import PatternDiscoveryEngine, OptimizedPattern
from cryptoswarms.edge.edge_quantifier import EdgeQuantifier, EdgeMetrics, DeploymentCriteria
from cryptoswarms.backtest.real_engine import RealBacktestEngine

logger = logging.getLogger("cryptoswarms.alpha_discovery")

@dataclass
class AlphaDiscoveryResult:
    """Complete alpha discovery result."""
    symbol: str
    interval: str
    discovery_timestamp: datetime
    patterns_discovered: int
    patterns_validated: int
    patterns_deployed: int
    deployed_patterns: List['DeployedPattern']
    performance_summary: Dict[str, float]

@dataclass
class DeployedPattern:
    """A pattern approved for live trading."""
    pattern: OptimizedPattern
    edge_metrics: EdgeMetrics
    deployment_timestamp: datetime
    risk_limits: Any
    expected_annual_return: float
    max_position_size: float

class AlphaDiscoveryEngine:
    """Main engine that orchestrates the complete alpha discovery pipeline."""
    
    def __init__(
        self,
        binance_client,
        timescale_db,
        redis_client=None
    ):
        # Core components
        self.historical_engine = HistoricalDataEngine(binance_client, timescale_db)
        self.pattern_discovery = PatternDiscoveryEngine(self.historical_engine)
        self.edge_quantifier = EdgeQuantifier()
        self.deployment_criteria = DeploymentCriteria()
        self.backtest_engine = RealBacktestEngine(self.historical_engine)
        self.regime_classifier = MarketRegimeClassifier()
        
        # Cache for validated patterns
        self.validated_patterns: Dict[str, DeployedPattern] = {}
        
    async def discover_alpha(
        self,
        symbols: List[str] = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"],
        intervals: List[str] = ["15m", "1h"],
        lookback_days: int = 365,
        min_deployment_score: float = 0.7
    ) -> List[AlphaDiscoveryResult]:
        """Complete alpha discovery pipeline."""
        
        logger.info(f"Starting alpha discovery for {len(symbols)} symbols, {len(intervals)} intervals")
        
        # Step 1: Build historical dataset
        logger.info("Step 1: Building historical dataset...")
        await self._ensure_historical_data(symbols, intervals, lookback_days)
        
        results = []
        
        for symbol in symbols:
            for interval in intervals:
                logger.info(f"Discovering alpha for {symbol} {interval}")
                
                try:
                    result = await self._discover_alpha_for_symbol(
                        symbol=symbol,
                        interval=interval,
                        lookback_days=lookback_days,
                        min_deployment_score=min_deployment_score
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error discovering alpha for {symbol} {interval}: {e}")
                    continue
        
        # Summary
        total_discovered = sum(r.patterns_discovered for r in results)
        total_validated = sum(r.patterns_validated for r in results)
        total_deployed = sum(r.patterns_deployed for r in results)
        
        logger.info(f"Alpha discovery complete: {total_discovered} discovered, "
                   f"{total_validated} validated, {total_deployed} deployed")
        
        return results
    
    async def _discover_alpha_for_symbol(
        self,
        symbol: str,
        interval: str,
        lookback_days: int,
        min_deployment_score: float
    ) -> AlphaDiscoveryResult:
        """Discover alpha for a single symbol/interval combination."""
        
        discovery_start = datetime.now(timezone.utc)
        
        # Step 2: Pattern Discovery
        logger.info(f"Step 2: Discovering patterns for {symbol} {interval}")
        optimized_patterns = self.pattern_discovery.discover_all_patterns(
            symbol=symbol,
            interval=interval,
            lookback_days=lookback_days
        )
        
        if not optimized_patterns:
            logger.warning(f"No patterns discovered for {symbol} {interval}")
            return AlphaDiscoveryResult(
                symbol=symbol,
                interval=interval,
                discovery_timestamp=discovery_start,
                patterns_discovered=0,
                patterns_validated=0,
                patterns_deployed=0,
                deployed_patterns=[],
                performance_summary={}
            )
        
        # Step 3: Edge Quantification & Validation
        logger.info(f"Step 3: Quantifying edge for {len(optimized_patterns)} patterns")
        validated_patterns = []
        
        for pattern in optimized_patterns:
            try:
                # Calculate comprehensive edge metrics
                edge_metrics = self.edge_quantifier.calculate_edge_metrics(
                    signals=pattern.signals,
                    data=pattern.data,
                    symbol=symbol
                )
                
                # Check deployment criteria
                deployment_decision = self.deployment_criteria.evaluate_pattern_for_deployment(
                    edge_metrics=edge_metrics
                )
                
                if deployment_decision.approved and edge_metrics.deployment_score >= min_deployment_score:
                    # Run final backtest validation
                    backtest_result = await self._validate_with_backtest(pattern, symbol, interval)
                    
                    if backtest_result and backtest_result.performance.sharpe_ratio > 1.5:
                        deployed_pattern = DeployedPattern(
                            pattern=pattern,
                            edge_metrics=edge_metrics,
                            deployment_timestamp=datetime.now(timezone.utc),
                            risk_limits=deployment_decision.risk_limits,
                            expected_annual_return=edge_metrics.expected_return_annualized,
                            max_position_size=deployment_decision.risk_limits.max_position_size_usd
                        )
                        validated_patterns.append(deployed_pattern)
                        
                        # Cache for live trading
                        pattern_key = f"{symbol}_{interval}_{pattern.pattern_name}"
                        self.validated_patterns[pattern_key] = deployed_pattern
                        
                        logger.info(f"✅ Pattern deployed: {pattern.pattern_name} for {symbol} "
                                  f"(Expected return: {edge_metrics.expected_return_annualized:.1%}, "
                                  f"Sharpe: {edge_metrics.sharpe_ratio:.2f})")
                    else:
                        logger.info(f"❌ Pattern failed backtest validation: {pattern.pattern_name}")
                else:
                    logger.info(f"❌ Pattern failed deployment criteria: {pattern.pattern_name} "
                              f"(Score: {edge_metrics.deployment_score:.2f})")
                    
            except Exception as e:
                logger.error(f"Error validating pattern {pattern.pattern_name}: {e}")
                continue
        
        # Performance summary
        if validated_patterns:
            performance_summary = {
                'avg_expected_return': sum(p.expected_annual_return for p in validated_patterns) / len(validated_patterns),
                'avg_sharpe_ratio': sum(p.edge_metrics.sharpe_ratio for p in validated_patterns) / len(validated_patterns),
                'avg_win_rate': sum(p.edge_metrics.win_rate for p in validated_patterns) / len(validated_patterns),
                'max_drawdown': max(p.edge_metrics.max_drawdown for p in validated_patterns),
                'total_expected_trades_per_day': sum(p.edge_metrics.trade_frequency_per_day for p in validated_patterns)
            }
        else:
            performance_summary = {}
        
        return AlphaDiscoveryResult(
            symbol=symbol,
            interval=interval,
            discovery_timestamp=discovery_start,
            patterns_discovered=len(optimized_patterns),
            patterns_validated=len([p for p in optimized_patterns if p.validation_result.is_significant]),
            patterns_deployed=len(validated_patterns),
            deployed_patterns=validated_patterns,
            performance_summary=performance_summary
        )
    
    async def _ensure_historical_data(
        self,
        symbols: List[str],
        intervals: List[str],
        lookback_days: int
    ):
        """Ensure we have sufficient historical data."""
        
        logger.info("Checking historical data availability...")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)
        
        for symbol in symbols:
            for interval in intervals:
                # Check if we have recent data
                existing_data = await self.historical_engine.query_data(
                    symbol=symbol,
                    interval=interval,
                    start_time=end_time - timedelta(days=7),  # Check last week
                    end_time=end_time
                )
                
                if existing_data.empty or len(existing_data) < 100:
                    logger.info(f"Fetching historical data for {symbol} {interval}")
                    
                    # Fetch and store historical data
                    historical_data = await self.historical_engine.fetch_ohlcv(
                        symbol=symbol,
                        interval=interval,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if not historical_data.empty:
                        await self.historical_engine.store_ohlcv(historical_data, symbol, interval)
                        
                        # Validate data quality
                        quality_report = self.historical_engine.validate_data_quality(
                            historical_data, symbol, interval
                        )
                        
                        if quality_report.quality_score < 0.8:
                            logger.warning(f"Data quality issues for {symbol} {interval}: "
                                         f"Score {quality_report.quality_score:.2f}")
                        else:
                            logger.info(f"✅ High quality data for {symbol} {interval}: "
                                      f"{len(historical_data)} candles, quality {quality_report.quality_score:.2f}")
    
    async def _validate_with_backtest(
        self,
        pattern: OptimizedPattern,
        symbol: str,
        interval: str
    ) -> Optional[Any]:
        """Final validation with comprehensive backtesting."""
        
        try:
            # Use last 6 months for final validation
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=180)
            
            backtest_result = self.backtest_engine.backtest_pattern(
                pattern=pattern,
                symbol=symbol,
                interval=interval,
                start_date=start_time,
                end_date=end_time
            )
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"Backtest validation failed for {pattern.pattern_name}: {e}")
            return None
    
    def get_deployed_patterns(self, symbol: str = None) -> List[DeployedPattern]:
        """Get all deployed patterns, optionally filtered by symbol."""
        
        if symbol:
            return [p for key, p in self.validated_patterns.items() if symbol in key]
        else:
            return list(self.validated_patterns.values())
    
    def get_pattern_for_trading(self, symbol: str, interval: str, pattern_name: str) -> Optional[DeployedPattern]:
        """Get a specific deployed pattern for live trading."""
        
        pattern_key = f"{symbol}_{interval}_{pattern_name}"
        return self.validated_patterns.get(pattern_key)
    
    async def refresh_patterns(self, max_age_days: int = 30):
        """Refresh patterns that are older than max_age_days."""
        
        current_time = datetime.now(timezone.utc)
        
        patterns_to_refresh = []
        for key, deployed_pattern in self.validated_patterns.items():
            age = (current_time - deployed_pattern.deployment_timestamp).days
            if age > max_age_days:
                patterns_to_refresh.append(key)
        
        if patterns_to_refresh:
            logger.info(f"Refreshing {len(patterns_to_refresh)} old patterns")
            
            for pattern_key in patterns_to_refresh:
                symbol, interval, pattern_name = pattern_key.split('_', 2)
                
                # Re-run discovery for this symbol/interval
                try:
                    await self._discover_alpha_for_symbol(
                        symbol=symbol,
                        interval=interval,
                        lookback_days=365,
                        min_deployment_score=0.7
                    )
                except Exception as e:
                    logger.error(f"Error refreshing pattern {pattern_key}: {e}")
    
    def generate_alpha_report(self) -> Dict[str, Any]:
        """Generate comprehensive alpha discovery report."""
        
        if not self.validated_patterns:
            return {"status": "No validated patterns deployed"}
        
        patterns = list(self.validated_patterns.values())
        
        return {
            "total_patterns": len(patterns),
            "symbols_covered": len(set(p.pattern.data.attrs.get('symbol', 'UNKNOWN') for p in patterns)),
            "avg_expected_return": sum(p.expected_annual_return for p in patterns) / len(patterns),
            "avg_sharpe_ratio": sum(p.edge_metrics.sharpe_ratio for p in patterns) / len(patterns),
            "avg_win_rate": sum(p.edge_metrics.win_rate for p in patterns) / len(patterns),
            "total_expected_trades_per_day": sum(p.edge_metrics.trade_frequency_per_day for p in patterns),
            "max_total_position_size": sum(p.max_position_size for p in patterns),
            "deployment_scores": [p.edge_metrics.deployment_score for p in patterns],
            "pattern_breakdown": {
                p.pattern.pattern_name: {
                    "expected_return": p.expected_annual_return,
                    "sharpe_ratio": p.edge_metrics.sharpe_ratio,
                    "win_rate": p.edge_metrics.win_rate,
                    "max_drawdown": p.edge_metrics.max_drawdown
                }
                for p in patterns
            }
        }