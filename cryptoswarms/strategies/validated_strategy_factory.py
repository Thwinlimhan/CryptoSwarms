"""Validated Strategy Factory for CryptoSwarms.

Creates strategies using statistically validated patterns instead of hardcoded parameters.
Replaces the old hardcoded strategy system with real alpha-based strategies.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from cryptoswarms.common.strategy import BaseStrategy
from cryptoswarms.alpha_discovery_engine import AlphaDiscoveryEngine, DeployedPattern

logger = logging.getLogger("cryptoswarms.strategies.validated")

@dataclass
class ValidatedStrategyConfig:
    """Configuration for a validated strategy."""
    strategy_id: str
    pattern_name: str
    symbol: str
    interval: str
    parameters: Dict[str, Any]
    edge_metrics: Dict[str, float]
    risk_limits: Dict[str, float]
    deployment_timestamp: datetime
    expected_return: float
    confidence_level: float

class ValidatedBollingerBreakoutStrategy(BaseStrategy):
    """Bollinger Breakout strategy using statistically validated parameters."""
    
    def __init__(self, deployed_pattern: DeployedPattern):
        self.deployed_pattern = deployed_pattern
        self.pattern = deployed_pattern.pattern
        self.edge_metrics = deployed_pattern.edge_metrics
        self.risk_limits = deployed_pattern.risk_limits
        
        # Use REAL optimized parameters instead of hardcoded ones
        params = self.pattern.optimal_parameters
        self.period = params['period']                    # e.g., 18 (not hardcoded 20)
        self.std_dev = params['std_dev']                  # e.g., 2.3 (not hardcoded 2.5)
        self.volume_filter = params['volume_filter']      # e.g., 1.4x (not ignored)
        self.min_breakout_pct = params['min_breakout_pct'] # e.g., 0.002 (validated)
        
        # Use REAL validated edge metrics
        self.expected_return = self.edge_metrics.expected_return_per_trade
        self.win_rate = self.edge_metrics.win_rate
        self.sharpe_ratio = self.edge_metrics.sharpe_ratio
        self.max_drawdown = self.edge_metrics.max_drawdown
        
        # Strategy configuration
        self.config = ValidatedStrategyConfig(
            strategy_id=f"validated-bollinger-{self.pattern.data.attrs.get('symbol', 'UNKNOWN')}",
            pattern_name=self.pattern.pattern_name,
            symbol=self.pattern.data.attrs.get('symbol', 'UNKNOWN'),
            interval="15m",  # TODO: Get from pattern
            parameters=params,
            edge_metrics={
                'expected_return': self.expected_return,
                'win_rate': self.win_rate,
                'sharpe_ratio': self.sharpe_ratio,
                'max_drawdown': self.max_drawdown
            },
            risk_limits={
                'max_position_size': self.risk_limits.max_position_size_usd,
                'max_daily_trades': self.risk_limits.max_daily_trades,
                'stop_loss_threshold': self.risk_limits.stop_loss_threshold
            },
            deployment_timestamp=deployed_pattern.deployment_timestamp,
            expected_return=self.expected_return,
            confidence_level=1 - self.edge_metrics.p_value  # Statistical confidence
        )
        
        logger.info(f"Initialized validated Bollinger strategy: "
                   f"period={self.period}, std_dev={self.std_dev}, "
                   f"expected_return={self.expected_return:.2%}, "
                   f"sharpe={self.sharpe_ratio:.2f}")
    
    async def evaluate(self, signal: dict, context: dict) -> dict:
        """Evaluate signal using validated parameters and real edge metrics."""
        
        # Only trade if pattern is still valid and meets deployment criteria
        if not self.deployed_pattern.edge_metrics.deployment_approved:
            logger.warning(f"Pattern no longer approved for deployment: {self.pattern.pattern_name}")
            return None
        
        # Check if signal matches our validated pattern
        if signal.get('signal_type') != 'bollinger_breakout':
            return None
        
        # Use real statistical confidence for position sizing
        confidence = min(0.95, self.config.confidence_level)
        
        # Risk management based on validated metrics
        position_size_multiplier = 1.0
        
        # Reduce size if recent performance is below expectation
        if context.get('recent_win_rate', self.win_rate) < self.win_rate * 0.8:
            position_size_multiplier *= 0.5
            logger.info("Reducing position size due to recent underperformance")
        
        # Reduce size if approaching daily trade limit
        daily_trades = context.get('daily_trades', 0)
        if daily_trades >= self.risk_limits.max_daily_trades * 0.8:
            position_size_multiplier *= 0.5
            logger.info("Reducing position size due to daily trade limit")
        
        return {
            "action": "BUY" if signal.get('direction') == 'long' else "SELL",
            "confidence": confidence,
            "position_size_multiplier": position_size_multiplier,
            "expected_return": self.expected_return,
            "stop_loss_pct": self.risk_limits.stop_loss_threshold,
            "take_profit_pct": self.expected_return * 2,  # 2x expected return
            "max_hold_time": 48,  # Based on pattern analysis
            "risk_metrics": {
                "max_drawdown": self.max_drawdown,
                "sharpe_ratio": self.sharpe_ratio,
                "win_rate": self.win_rate
            },
            "validation_info": {
                "pattern_name": self.pattern.pattern_name,
                "deployment_timestamp": self.deployment_timestamp.isoformat(),
                "statistical_significance": self.edge_metrics.p_value < 0.05,
                "sample_size": self.edge_metrics.sample_size
            }
        }

class ValidatedRSIMeanReversionStrategy(BaseStrategy):
    """RSI Mean Reversion strategy using statistically validated parameters."""
    
    def __init__(self, deployed_pattern: DeployedPattern):
        self.deployed_pattern = deployed_pattern
        self.pattern = deployed_pattern.pattern
        self.edge_metrics = deployed_pattern.edge_metrics
        self.risk_limits = deployed_pattern.risk_limits
        
        # Use REAL optimized parameters
        params = self.pattern.optimal_parameters
        self.rsi_period = params['rsi_period']            # e.g., 16 (not hardcoded 14)
        self.oversold_level = params['oversold_level']    # e.g., 28 (not hardcoded 30)
        self.overbought_level = params['overbought_level'] # e.g., 72 (not hardcoded 70)
        self.exit_rsi = params['exit_rsi']                # e.g., 52 (validated)
        self.volume_filter = params['volume_filter']      # e.g., 1.3x (validated)
        
        # Use REAL validated edge metrics
        self.expected_return = self.edge_metrics.expected_return_per_trade
        self.win_rate = self.edge_metrics.win_rate
        self.sharpe_ratio = self.edge_metrics.sharpe_ratio
        
        logger.info(f"Initialized validated RSI strategy: "
                   f"period={self.rsi_period}, oversold={self.oversold_level}, "
                   f"expected_return={self.expected_return:.2%}")
    
    async def evaluate(self, signal: dict, context: dict) -> dict:
        """Evaluate RSI signal using validated parameters."""
        
        if not self.deployed_pattern.edge_metrics.deployment_approved:
            return None
        
        if signal.get('signal_type') != 'rsi_mean_reversion':
            return None
        
        # Use validated confidence
        confidence = min(0.95, 1 - self.edge_metrics.p_value)
        
        return {
            "action": "BUY" if signal.get('direction') == 'long' else "SELL",
            "confidence": confidence,
            "expected_return": self.expected_return,
            "stop_loss_pct": self.risk_limits.stop_loss_threshold,
            "take_profit_pct": self.expected_return * 1.5,
            "risk_metrics": {
                "sharpe_ratio": self.sharpe_ratio,
                "win_rate": self.win_rate
            }
        }

class ValidatedStrategyFactory:
    """Factory for creating strategies from validated patterns."""
    
    def __init__(self, alpha_discovery_engine: AlphaDiscoveryEngine):
        self.alpha_engine = alpha_discovery_engine
        self.active_strategies: Dict[str, BaseStrategy] = {}
    
    def create_strategies_for_symbol(self, symbol: str, interval: str = "15m") -> List[BaseStrategy]:
        """Create all validated strategies for a symbol."""
        
        deployed_patterns = self.alpha_engine.get_deployed_patterns(symbol)
        strategies = []
        
        for deployed_pattern in deployed_patterns:
            try:
                strategy = self._create_strategy_from_pattern(deployed_pattern)
                if strategy:
                    strategies.append(strategy)
                    
                    # Cache active strategy
                    strategy_key = f"{symbol}_{interval}_{deployed_pattern.pattern.pattern_name}"
                    self.active_strategies[strategy_key] = strategy
                    
            except Exception as e:
                logger.error(f"Error creating strategy from pattern {deployed_pattern.pattern.pattern_name}: {e}")
                continue
        
        logger.info(f"Created {len(strategies)} validated strategies for {symbol}")
        return strategies
    
    def _create_strategy_from_pattern(self, deployed_pattern: DeployedPattern) -> Optional[BaseStrategy]:
        """Create appropriate strategy based on pattern type."""
        
        pattern_name = deployed_pattern.pattern.pattern_name
        
        if pattern_name == "bollinger_breakout":
            return ValidatedBollingerBreakoutStrategy(deployed_pattern)
        elif pattern_name == "rsi_mean_reversion":
            return ValidatedRSIMeanReversionStrategy(deployed_pattern)
        else:
            logger.warning(f"Unknown pattern type: {pattern_name}")
            return None
    
    def get_strategy(self, symbol: str, interval: str, pattern_name: str) -> Optional[BaseStrategy]:
        """Get a specific active strategy."""
        
        strategy_key = f"{symbol}_{interval}_{pattern_name}"
        return self.active_strategies.get(strategy_key)
    
    def refresh_strategies(self):
        """Refresh all strategies with latest validated patterns."""
        
        logger.info("Refreshing strategies with latest validated patterns")
        
        # Get all unique symbols from current strategies
        symbols = set()
        for key in self.active_strategies.keys():
            symbol = key.split('_')[0]
            symbols.add(symbol)
        
        # Recreate strategies for each symbol
        new_strategies = {}
        for symbol in symbols:
            strategies = self.create_strategies_for_symbol(symbol)
            for strategy in strategies:
                if hasattr(strategy, 'config'):
                    key = f"{strategy.config.symbol}_{strategy.config.interval}_{strategy.config.pattern_name}"
                    new_strategies[key] = strategy
        
        # Replace old strategies
        self.active_strategies = new_strategies
        logger.info(f"Refreshed {len(new_strategies)} strategies")
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of all active strategies."""
        
        if not self.active_strategies:
            return {"status": "No active strategies"}
        
        strategies = list(self.active_strategies.values())
        
        return {
            "total_strategies": len(strategies),
            "avg_expected_return": sum(s.expected_return for s in strategies if hasattr(s, 'expected_return')) / len(strategies),
            "avg_sharpe_ratio": sum(s.sharpe_ratio for s in strategies if hasattr(s, 'sharpe_ratio')) / len(strategies),
            "avg_win_rate": sum(s.win_rate for s in strategies if hasattr(s, 'win_rate')) / len(strategies),
            "strategy_breakdown": {
                key: {
                    "expected_return": getattr(strategy, 'expected_return', 0),
                    "sharpe_ratio": getattr(strategy, 'sharpe_ratio', 0),
                    "win_rate": getattr(strategy, 'win_rate', 0)
                }
                for key, strategy in self.active_strategies.items()
            }
        }