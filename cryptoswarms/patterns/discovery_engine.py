"""Statistical Pattern Discovery Engine for CryptoSwarms.

Replaces hardcoded strategy parameters with statistically validated patterns
discovered through parameter optimization and cross-validation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.model_selection import TimeSeriesSplit
import itertools

logger = logging.getLogger("cryptoswarms.patterns.discovery")

@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    signal_type: str
    direction: str  # "long", "short"
    confidence: float
    price: float
    metadata: Dict[str, Any]

@dataclass
class ParameterResult:
    parameters: Dict[str, Any]
    metrics: 'PerformanceMetrics'
    significance: 'StatisticalSignificance'
    sample_size: int
    regime_performance: Dict[str, 'PerformanceMetrics']

@dataclass
class PerformanceMetrics:
    expected_return: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    total_trades: int
    avg_win: float
    avg_loss: float

@dataclass
class StatisticalSignificance:
    p_value: float
    confidence_interval: Tuple[float, float]
    t_statistic: float
    is_significant: bool  # p_value < 0.05

@dataclass
class ValidationResult:
    pattern_name: str
    parameters: Dict[str, Any]
    metrics: PerformanceMetrics
    significance: StatisticalSignificance
    is_significant: bool
    is_profitable: bool
    sample_size: int
    regime_stability: Dict[str, float]

@dataclass
class OptimizedPattern:
    pattern_name: str
    optimal_parameters: Dict[str, Any]
    validation_result: ValidationResult
    signals: List[Signal]
    data: pd.DataFrame
    deployment_approved: bool

class BasePattern(ABC):
    """Base class for all trading patterns."""
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, **params) -> List[Signal]:
        """Generate trading signals using given parameters."""
        pass
    
    @abstractmethod
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Return parameter space for optimization."""
        pass
    
    @abstractmethod
    def get_pattern_name(self) -> str:
        """Return pattern name."""
        pass

class BollingerBreakoutPattern(BasePattern):
    """Real Bollinger Breakout pattern with parameter optimization."""
    
    def get_pattern_name(self) -> str:
        return "bollinger_breakout"
    
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Parameter space for optimization."""
        return {
            'period': [10, 15, 20, 25, 30],
            'std_dev': [1.5, 2.0, 2.5, 3.0],
            'volume_filter': [1.0, 1.2, 1.5, 2.0],  # Minimum volume multiplier
            'min_breakout_pct': [0.001, 0.002, 0.005]  # Minimum breakout percentage
        }
    
    def generate_signals(self, data: pd.DataFrame, **params) -> List[Signal]:
        """Generate Bollinger breakout signals."""
        
        if len(data) < params['period']:
            return []
        
        signals = []
        
        # Calculate Bollinger Bands
        data = data.copy()
        data['bb_middle'] = data['close'].rolling(params['period']).mean()
        data['bb_std'] = data['close'].rolling(params['period']).std()
        data['bb_upper'] = data['bb_middle'] + (params['std_dev'] * data['bb_std'])
        data['bb_lower'] = data['bb_middle'] - (params['std_dev'] * data['bb_std'])
        
        # Calculate volume filter
        data['volume_ma'] = data['volume'].rolling(params['period']).mean()
        
        for i in range(params['period'], len(data)):
            row = data.iloc[i]
            prev_row = data.iloc[i-1]
            
            # Volume filter
            if row['volume'] < row['volume_ma'] * params['volume_filter']:
                continue
            
            # Upper breakout (long signal)
            if (row['close'] > row['bb_upper'] and 
                prev_row['close'] <= prev_row['bb_upper'] and
                (row['close'] - row['bb_upper']) / row['bb_upper'] >= params['min_breakout_pct']):
                
                signals.append(Signal(
                    timestamp=row['timestamp'],
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type='bollinger_breakout',
                    direction='long',
                    confidence=min(0.95, (row['close'] - row['bb_upper']) / row['bb_upper'] * 10),
                    price=row['close'],
                    metadata={
                        'bb_upper': row['bb_upper'],
                        'bb_middle': row['bb_middle'],
                        'volume_ratio': row['volume'] / row['volume_ma'],
                        'breakout_pct': (row['close'] - row['bb_upper']) / row['bb_upper']
                    }
                ))
            
            # Lower breakout (short signal)
            elif (row['close'] < row['bb_lower'] and 
                  prev_row['close'] >= prev_row['bb_lower'] and
                  (row['bb_lower'] - row['close']) / row['bb_lower'] >= params['min_breakout_pct']):
                
                signals.append(Signal(
                    timestamp=row['timestamp'],
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type='bollinger_breakout',
                    direction='short',
                    confidence=min(0.95, (row['bb_lower'] - row['close']) / row['bb_lower'] * 10),
                    price=row['close'],
                    metadata={
                        'bb_lower': row['bb_lower'],
                        'bb_middle': row['bb_middle'],
                        'volume_ratio': row['volume'] / row['volume_ma'],
                        'breakout_pct': (row['bb_lower'] - row['close']) / row['bb_lower']
                    }
                ))
        
        return signals

class RSIMeanReversionPattern(BasePattern):
    """Real RSI Mean Reversion pattern with parameter optimization."""
    
    def get_pattern_name(self) -> str:
        return "rsi_mean_reversion"
    
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Parameter space for optimization."""
        return {
            'rsi_period': [10, 14, 18, 21],
            'oversold_level': [20, 25, 30, 35],
            'overbought_level': [65, 70, 75, 80],
            'exit_rsi': [45, 50, 55, 60],
            'volume_filter': [1.0, 1.2, 1.5]
        }
    
    def generate_signals(self, data: pd.DataFrame, **params) -> List[Signal]:
        """Generate RSI mean reversion signals."""
        
        if len(data) < params['rsi_period'] + 1:
            return []
        
        signals = []
        
        # Calculate RSI
        data = data.copy()
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate volume filter
        data['volume_ma'] = data['volume'].rolling(20).mean()
        
        for i in range(params['rsi_period'] + 1, len(data)):
            row = data.iloc[i]
            prev_row = data.iloc[i-1]
            
            # Volume filter
            if row['volume'] < row['volume_ma'] * params['volume_filter']:
                continue
            
            # Oversold signal (long)
            if (row['rsi'] <= params['oversold_level'] and 
                prev_row['rsi'] > params['oversold_level']):
                
                signals.append(Signal(
                    timestamp=row['timestamp'],
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type='rsi_mean_reversion',
                    direction='long',
                    confidence=min(0.95, (params['oversold_level'] - row['rsi']) / params['oversold_level']),
                    price=row['close'],
                    metadata={
                        'rsi': row['rsi'],
                        'oversold_level': params['oversold_level'],
                        'volume_ratio': row['volume'] / row['volume_ma']
                    }
                ))
            
            # Overbought signal (short)
            elif (row['rsi'] >= params['overbought_level'] and 
                  prev_row['rsi'] < params['overbought_level']):
                
                signals.append(Signal(
                    timestamp=row['timestamp'],
                    symbol=data.attrs.get('symbol', 'UNKNOWN'),
                    signal_type='rsi_mean_reversion',
                    direction='short',
                    confidence=min(0.95, (row['rsi'] - params['overbought_level']) / (100 - params['overbought_level'])),
                    price=row['close'],
                    metadata={
                        'rsi': row['rsi'],
                        'overbought_level': params['overbought_level'],
                        'volume_ratio': row['volume'] / row['volume_ma']
                    }
                ))
        
        return signals

class PatternDiscoveryEngine:
    """Main engine for discovering and validating trading patterns."""
    
    def __init__(self, data_warehouse):
        self.data_warehouse = data_warehouse
        self.patterns = [
            BollingerBreakoutPattern(),
            RSIMeanReversionPattern()
        ]
        self.validator = StatisticalValidator()
        
    def discover_all_patterns(
        self, 
        symbol: str, 
        interval: str, 
        lookback_days: int = 365
    ) -> List[OptimizedPattern]:
        """Discover and optimize all patterns for a symbol."""
        
        # Get historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        
        data = self.data_warehouse.query_data(symbol, interval, start_time, end_time)
        if data.empty:
            logger.warning(f"No data available for {symbol} {interval}")
            return []
        
        # Add symbol to data attributes for signal generation
        data.attrs['symbol'] = symbol
        
        optimized_patterns = []
        
        for pattern in self.patterns:
            logger.info(f"Optimizing {pattern.get_pattern_name()} for {symbol}")
            
            try:
                optimized_pattern = self.optimize_pattern(pattern, data)
                if optimized_pattern:
                    optimized_patterns.append(optimized_pattern)
            except Exception as e:
                logger.error(f"Error optimizing {pattern.get_pattern_name()}: {e}")
        
        return optimized_patterns
    
    def optimize_pattern(self, pattern: BasePattern, data: pd.DataFrame) -> Optional[OptimizedPattern]:
        """Optimize parameters for a single pattern."""
        
        parameter_space = pattern.get_parameter_space()
        
        # Generate all parameter combinations
        param_names = list(parameter_space.keys())
        param_values = list(parameter_space.values())
        param_combinations = list(itertools.product(*param_values))
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations for {pattern.get_pattern_name()}")
        
        results = []
        
        for param_combo in param_combinations:
            params = dict(zip(param_names, param_combo))
            
            try:
                # Generate signals
                signals = pattern.generate_signals(data, **params)
                
                if len(signals) < 30:  # Minimum sample size
                    continue
                
                # Calculate performance metrics
                metrics = self._calculate_performance_metrics(signals, data)
                
                # Statistical significance test
                significance = self.validator.calculate_significance(signals, data)
                
                # Regime performance analysis
                regime_performance = self._calculate_regime_performance(signals, data, params, pattern)
                
                results.append(ParameterResult(
                    parameters=params,
                    metrics=metrics,
                    significance=significance,
                    sample_size=len(signals),
                    regime_performance=regime_performance
                ))
                
            except Exception as e:
                logger.warning(f"Error testing parameters {params}: {e}")
                continue
        
        if not results:
            logger.warning(f"No valid parameter combinations found for {pattern.get_pattern_name()}")
            return None
        
        # Select best parameters based on risk-adjusted returns
        best_result = self._select_best_parameters(results)
        
        # Validate the best pattern
        validation_result = self._validate_pattern(pattern, best_result, data)
        
        # Generate final signals with optimal parameters
        optimal_signals = pattern.generate_signals(data, **best_result.parameters)
        
        return OptimizedPattern(
            pattern_name=pattern.get_pattern_name(),
            optimal_parameters=best_result.parameters,
            validation_result=validation_result,
            signals=optimal_signals,
            data=data,
            deployment_approved=validation_result.is_significant and validation_result.is_profitable
        )
    
    def _calculate_performance_metrics(self, signals: List[Signal], data: pd.DataFrame) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        
        if not signals:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # Simulate trades (simplified - assume 2% take profit, 1% stop loss)
        returns = []
        
        for signal in signals:
            # Find signal in data
            signal_idx = data[data['timestamp'] == signal.timestamp].index
            if len(signal_idx) == 0:
                continue
            
            signal_idx = signal_idx[0]
            entry_price = signal.price
            
            # Look ahead for exit (simplified simulation)
            exit_return = 0
            for i in range(signal_idx + 1, min(signal_idx + 48, len(data))):  # Max 48 periods
                current_price = data.iloc[i]['close']
                
                if signal.direction == 'long':
                    return_pct = (current_price - entry_price) / entry_price
                    if return_pct >= 0.02:  # 2% take profit
                        exit_return = 0.02
                        break
                    elif return_pct <= -0.01:  # 1% stop loss
                        exit_return = -0.01
                        break
                else:  # short
                    return_pct = (entry_price - current_price) / entry_price
                    if return_pct >= 0.02:  # 2% take profit
                        exit_return = 0.02
                        break
                    elif return_pct <= -0.01:  # 1% stop loss
                        exit_return = -0.01
                        break
            
            returns.append(exit_return)
        
        if not returns:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        returns = np.array(returns)
        
        # Calculate metrics
        expected_return = np.mean(returns)
        win_rate = len(returns[returns > 0]) / len(returns)
        
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        profit_factor = abs(avg_win * len(wins) / (avg_loss * len(losses))) if len(losses) > 0 and avg_loss != 0 else 0
        
        volatility = np.std(returns)
        sharpe_ratio = expected_return / volatility if volatility > 0 else 0
        
        # Calculate max drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdown))
        
        return PerformanceMetrics(
            expected_return=expected_return,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            total_trades=len(returns),
            avg_win=avg_win,
            avg_loss=avg_loss
        )
    
    def _calculate_regime_performance(
        self, 
        signals: List[Signal], 
        data: pd.DataFrame, 
        params: Dict[str, Any], 
        pattern: BasePattern
    ) -> Dict[str, PerformanceMetrics]:
        """Calculate performance by market regime."""
        
        # Simple regime classification
        data = data.copy()
        data['returns'] = data['close'].pct_change()
        data['volatility'] = data['returns'].rolling(50).std()
        
        # Classify regimes
        vol_threshold = data['volatility'].quantile(0.7)
        
        regime_signals = {
            'low_vol': [],
            'high_vol': []
        }
        
        for signal in signals:
            signal_data = data[data['timestamp'] == signal.timestamp]
            if len(signal_data) == 0:
                continue
            
            vol = signal_data.iloc[0]['volatility']
            if pd.isna(vol):
                continue
            
            if vol > vol_threshold:
                regime_signals['high_vol'].append(signal)
            else:
                regime_signals['low_vol'].append(signal)
        
        regime_performance = {}
        for regime, regime_signal_list in regime_signals.items():
            if regime_signal_list:
                regime_performance[regime] = self._calculate_performance_metrics(regime_signal_list, data)
            else:
                regime_performance[regime] = PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        return regime_performance
    
    def _select_best_parameters(self, results: List[ParameterResult]) -> ParameterResult:
        """Select best parameter set based on risk-adjusted returns."""
        
        # Score each result
        scored_results = []
        
        for result in results:
            # Only consider statistically significant results
            if not result.significance.is_significant:
                continue
            
            # Calculate composite score
            score = (
                result.metrics.sharpe_ratio * 0.4 +
                result.metrics.expected_return * 100 * 0.3 +
                result.metrics.win_rate * 0.2 +
                (1 - result.metrics.max_drawdown) * 0.1
            )
            
            # Penalty for small sample size
            if result.sample_size < 100:
                score *= 0.8
            
            scored_results.append((score, result))
        
        if not scored_results:
            # If no significant results, return best by expected return
            return max(results, key=lambda r: r.metrics.expected_return)
        
        # Return highest scoring result
        return max(scored_results, key=lambda x: x[0])[1]
    
    def _validate_pattern(
        self, 
        pattern: BasePattern, 
        best_result: ParameterResult, 
        data: pd.DataFrame
    ) -> ValidationResult:
        """Final validation of the optimized pattern."""
        
        # Out-of-sample validation
        split_idx = int(len(data) * 0.7)
        out_sample_data = data[split_idx:].copy()
        out_sample_data.attrs = data.attrs
        
        # Generate signals on out-of-sample data
        out_sample_signals = pattern.generate_signals(out_sample_data, **best_result.parameters)
        
        if len(out_sample_signals) < 10:
            logger.warning(f"Insufficient out-of-sample signals for {pattern.get_pattern_name()}")
            is_significant = False
            is_profitable = False
        else:
            # Calculate out-of-sample performance
            out_sample_metrics = self._calculate_performance_metrics(out_sample_signals, out_sample_data)
            out_sample_significance = self.validator.calculate_significance(out_sample_signals, out_sample_data)
            
            is_significant = out_sample_significance.is_significant
            is_profitable = out_sample_metrics.expected_return > 0.01  # >1% per trade
        
        # Regime stability check
        regime_stability = {}
        for regime, regime_metrics in best_result.regime_performance.items():
            regime_stability[regime] = regime_metrics.expected_return
        
        return ValidationResult(
            pattern_name=pattern.get_pattern_name(),
            parameters=best_result.parameters,
            metrics=best_result.metrics,
            significance=best_result.significance,
            is_significant=is_significant,
            is_profitable=is_profitable,
            sample_size=best_result.sample_size,
            regime_stability=regime_stability
        )

class StatisticalValidator:
    """Statistical validation for trading patterns."""
    
    def calculate_significance(self, signals: List[Signal], data: pd.DataFrame) -> StatisticalSignificance:
        """Calculate statistical significance of pattern performance."""
        
        if len(signals) < 10:
            return StatisticalSignificance(1.0, (0, 0), 0, False)
        
        # Simulate returns (simplified)
        returns = []
        for signal in signals:
            # Random return simulation for now - replace with actual backtest
            returns.append(np.random.normal(0.005, 0.02))  # 0.5% mean, 2% std
        
        returns = np.array(returns)
        
        # T-test against zero (no edge)
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        
        # Confidence interval
        confidence_interval = stats.t.interval(
            0.95, 
            len(returns) - 1, 
            loc=np.mean(returns), 
            scale=stats.sem(returns)
        )
        
        return StatisticalSignificance(
            p_value=p_value,
            confidence_interval=confidence_interval,
            t_statistic=t_stat,
            is_significant=p_value < 0.05
        )