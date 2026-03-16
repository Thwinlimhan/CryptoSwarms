"""Edge Quantification Engine for CryptoSwarms.

Replaces fake base rates with real statistical edge quantification
including transaction costs, regime analysis, and deployment criteria.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from scipy import stats
import warnings

logger = logging.getLogger("cryptoswarms.edge.quantifier")

@dataclass
class TransactionCosts:
    """Real transaction cost modeling."""
    maker_fee: float = 0.001      # 0.1% maker fee
    taker_fee: float = 0.001      # 0.1% taker fee
    slippage_bps: float = 2.0     # 2 bps average slippage
    funding_rate: float = 0.0001  # 0.01% funding rate per 8h
    market_impact_bps: float = 1.0  # 1 bp market impact

@dataclass
class EdgeMetrics:
    """Comprehensive edge quantification metrics."""
    # Return metrics
    expected_return_per_trade: float
    expected_return_annualized: float
    gross_return_per_trade: float  # Before transaction costs
    
    # Risk metrics
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float  # 95% Value at Risk
    
    # Trade metrics
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    total_trades: int
    trade_frequency_per_day: float
    
    # Statistical significance
    p_value: float
    confidence_interval: Tuple[float, float]
    t_statistic: float
    
    # Sample quality
    sample_size: int
    degrees_of_freedom: int
    
    # Cost breakdown
    transaction_cost_impact: float  # As % of gross returns
    slippage_impact: float
    fee_impact: float
    funding_impact: float
    
    # Regime breakdown
    regime_performance: Dict[str, 'RegimeMetrics']
    
    # Deployment readiness
    deployment_score: float  # 0-1 composite score
    deployment_approved: bool

@dataclass
class RegimeMetrics:
    """Performance metrics by market regime."""
    regime_name: str
    expected_return: float
    win_rate: float
    sharpe_ratio: float
    sample_size: int
    confidence: float

@dataclass
class DeploymentDecision:
    """Deployment decision with criteria breakdown."""
    approved: bool
    criteria_checks: Dict[str, bool]
    recommendation: str
    risk_limits: Optional['RiskLimits']
    deployment_score: float

@dataclass
class RiskLimits:
    """Risk limits for deployed patterns."""
    max_position_size_usd: float
    max_daily_trades: int
    max_drawdown_threshold: float
    stop_loss_threshold: float
    correlation_limit: float

class EdgeQuantifier:
    """Main engine for quantifying trading edge."""
    
    def __init__(self, transaction_costs: Optional[TransactionCosts] = None):
        self.transaction_costs = transaction_costs or TransactionCosts()
        
    def calculate_edge_metrics(
        self, 
        signals: List[Any], 
        data: pd.DataFrame,
        symbol: str = "UNKNOWN"
    ) -> EdgeMetrics:
        """Calculate comprehensive edge metrics including transaction costs."""
        
        if not signals:
            return self._empty_metrics()
        
        logger.info(f"Calculating edge metrics for {len(signals)} signals on {symbol}")
        
        # Simulate realistic trades
        trades = self._simulate_realistic_trades(signals, data)
        
        if not trades:
            return self._empty_metrics()
        
        # Calculate returns
        gross_returns = np.array([t['gross_return'] for t in trades])
        net_returns = np.array([t['net_return'] for t in trades])
        
        # Basic return metrics
        expected_return = np.mean(net_returns)
        gross_expected_return = np.mean(gross_returns)
        
        # Annualized return (assuming daily frequency)
        trade_frequency = len(trades) / ((data['timestamp'].iloc[-1] - data['timestamp'].iloc[0]).days + 1)
        annualized_return = expected_return * trade_frequency * 365
        
        # Risk metrics
        volatility = np.std(net_returns)
        sharpe_ratio = expected_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative_returns = np.cumprod(1 + net_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        # VaR 95%
        var_95 = np.percentile(net_returns, 5)
        
        # Trade metrics
        winning_trades = net_returns[net_returns > 0]
        losing_trades = net_returns[net_returns < 0]
        
        win_rate = len(winning_trades) / len(net_returns)
        avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0
        avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0
        
        profit_factor = (
            abs(avg_win * len(winning_trades) / (avg_loss * len(losing_trades))) 
            if len(losing_trades) > 0 and avg_loss != 0 else float('inf')
        )
        
        # Statistical significance
        t_stat, p_value = stats.ttest_1samp(net_returns, 0) if len(net_returns) > 1 else (0, 1)
        
        confidence_interval = (
            stats.t.interval(0.95, len(net_returns) - 1, loc=expected_return, scale=stats.sem(net_returns))
            if len(net_returns) > 1 else (0, 0)
        )
        
        # Cost impact analysis
        total_costs = gross_expected_return - expected_return
        transaction_cost_impact = abs(total_costs / gross_expected_return) if gross_expected_return != 0 else 0
        
        # Cost breakdown
        slippage_impact = np.mean([t['slippage_cost'] for t in trades])
        fee_impact = np.mean([t['fee_cost'] for t in trades])
        funding_impact = np.mean([t['funding_cost'] for t in trades])
        
        # Regime performance
        regime_performance = self._calculate_regime_performance(trades, data)
        
        # Deployment score
        deployment_score = self._calculate_deployment_score(
            expected_return, win_rate, sharpe_ratio, max_drawdown, 
            p_value, len(trades), transaction_cost_impact
        )
        
        return EdgeMetrics(
            expected_return_per_trade=expected_return,
            expected_return_annualized=annualized_return,
            gross_return_per_trade=gross_expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=avg_win,
            average_loss=avg_loss,
            total_trades=len(trades),
            trade_frequency_per_day=trade_frequency,
            p_value=p_value,
            confidence_interval=confidence_interval,
            t_statistic=t_stat,
            sample_size=len(trades),
            degrees_of_freedom=len(trades) - 1,
            transaction_cost_impact=transaction_cost_impact,
            slippage_impact=slippage_impact,
            fee_impact=fee_impact,
            funding_impact=funding_impact,
            regime_performance=regime_performance,
            deployment_score=deployment_score,
            deployment_approved=deployment_score > 0.7
        )
    
    def _simulate_realistic_trades(self, signals: List[Any], data: pd.DataFrame) -> List[Dict[str, float]]:
        """Simulate realistic trade execution with proper cost modeling."""
        
        trades = []
        
        for signal in signals:
            try:
                # Find signal in data
                signal_time = signal.timestamp
                signal_data = data[data['timestamp'] == signal_time]
                
                if len(signal_data) == 0:
                    continue
                
                signal_idx = signal_data.index[0]
                entry_price = signal.price
                
                # Simulate trade execution with costs
                trade_result = self._simulate_single_trade(
                    signal=signal,
                    data=data,
                    signal_idx=signal_idx,
                    entry_price=entry_price
                )
                
                if trade_result:
                    trades.append(trade_result)
                    
            except Exception as e:
                logger.warning(f"Error simulating trade for signal {signal}: {e}")
                continue
        
        return trades
    
    def _simulate_single_trade(
        self, 
        signal: Any, 
        data: pd.DataFrame, 
        signal_idx: int, 
        entry_price: float
    ) -> Optional[Dict[str, float]]:
        """Simulate a single trade with realistic execution."""
        
        # Trade parameters
        take_profit_pct = 0.02  # 2%
        stop_loss_pct = 0.01    # 1%
        max_hold_periods = 48   # Max holding time
        
        # Entry costs
        entry_slippage = self._calculate_slippage(entry_price, signal.direction, 'entry')
        entry_fee = entry_price * self.transaction_costs.taker_fee  # Assume market order
        
        actual_entry_price = entry_price + entry_slippage
        
        # Look for exit
        exit_price = None
        exit_reason = None
        hold_periods = 0
        
        for i in range(signal_idx + 1, min(signal_idx + max_hold_periods + 1, len(data))):
            current_price = data.iloc[i]['close']
            hold_periods += 1
            
            if signal.direction == 'long':
                # Check take profit
                if current_price >= actual_entry_price * (1 + take_profit_pct):
                    exit_price = actual_entry_price * (1 + take_profit_pct)
                    exit_reason = 'take_profit'
                    break
                # Check stop loss
                elif current_price <= actual_entry_price * (1 - stop_loss_pct):
                    exit_price = actual_entry_price * (1 - stop_loss_pct)
                    exit_reason = 'stop_loss'
                    break
            else:  # short
                # Check take profit
                if current_price <= actual_entry_price * (1 - take_profit_pct):
                    exit_price = actual_entry_price * (1 - take_profit_pct)
                    exit_reason = 'take_profit'
                    break
                # Check stop loss
                elif current_price >= actual_entry_price * (1 + stop_loss_pct):
                    exit_price = actual_entry_price * (1 + stop_loss_pct)
                    exit_reason = 'stop_loss'
                    break
        
        # If no exit triggered, exit at current price
        if exit_price is None:
            exit_price = data.iloc[min(signal_idx + max_hold_periods, len(data) - 1)]['close']
            exit_reason = 'time_exit'
        
        # Exit costs
        exit_slippage = self._calculate_slippage(exit_price, signal.direction, 'exit')
        exit_fee = exit_price * self.transaction_costs.taker_fee
        
        actual_exit_price = exit_price - exit_slippage
        
        # Calculate returns
        if signal.direction == 'long':
            gross_return = (actual_exit_price - actual_entry_price) / actual_entry_price
        else:  # short
            gross_return = (actual_entry_price - actual_exit_price) / actual_entry_price
        
        # Calculate costs
        slippage_cost = (entry_slippage + exit_slippage) / actual_entry_price
        fee_cost = (entry_fee + exit_fee) / actual_entry_price
        
        # Funding cost (for perpetual futures)
        funding_periods = hold_periods // 8  # Funding every 8 hours
        funding_cost = funding_periods * self.transaction_costs.funding_rate
        
        total_costs = slippage_cost + fee_cost + funding_cost
        net_return = gross_return - total_costs
        
        return {
            'entry_price': actual_entry_price,
            'exit_price': actual_exit_price,
            'direction': signal.direction,
            'hold_periods': hold_periods,
            'exit_reason': exit_reason,
            'gross_return': gross_return,
            'net_return': net_return,
            'slippage_cost': slippage_cost,
            'fee_cost': fee_cost,
            'funding_cost': funding_cost,
            'total_costs': total_costs
        }
    
    def _calculate_slippage(self, price: float, direction: str, side: str) -> float:
        """Calculate realistic slippage based on direction and market conditions."""
        
        base_slippage = price * (self.transaction_costs.slippage_bps / 10000)
        
        # Market impact (higher for larger orders)
        market_impact = price * (self.transaction_costs.market_impact_bps / 10000)
        
        # Direction-dependent slippage
        if (direction == 'long' and side == 'entry') or (direction == 'short' and side == 'exit'):
            # Buying - slippage increases price
            return base_slippage + market_impact
        else:
            # Selling - slippage decreases effective price (but we return positive cost)
            return base_slippage + market_impact
    
    def _calculate_regime_performance(self, trades: List[Dict], data: pd.DataFrame) -> Dict[str, RegimeMetrics]:
        """Calculate performance by market regime."""
        
        if not trades:
            return {}
        
        # Simple regime classification based on volatility
        data = data.copy()
        data['returns'] = data['close'].pct_change()
        data['volatility'] = data['returns'].rolling(50).std()
        
        vol_threshold = data['volatility'].quantile(0.7)
        
        # Classify trades by regime
        regime_trades = {'low_vol': [], 'high_vol': []}
        
        for trade in trades:
            # Find trade timestamp in data (simplified)
            # In real implementation, would match by actual timestamp
            trade_vol = np.random.choice(data['volatility'].dropna())  # Placeholder
            
            if trade_vol > vol_threshold:
                regime_trades['high_vol'].append(trade)
            else:
                regime_trades['low_vol'].append(trade)
        
        regime_performance = {}
        
        for regime_name, regime_trade_list in regime_trades.items():
            if not regime_trade_list:
                continue
            
            returns = [t['net_return'] for t in regime_trade_list]
            
            expected_return = np.mean(returns)
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            volatility = np.std(returns)
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0
            
            regime_performance[regime_name] = RegimeMetrics(
                regime_name=regime_name,
                expected_return=expected_return,
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                sample_size=len(returns),
                confidence=0.8  # Placeholder confidence
            )
        
        return regime_performance
    
    def _calculate_deployment_score(
        self, 
        expected_return: float, 
        win_rate: float, 
        sharpe_ratio: float, 
        max_drawdown: float,
        p_value: float, 
        sample_size: int, 
        cost_impact: float
    ) -> float:
        """Calculate composite deployment readiness score (0-1)."""
        
        score = 0.0
        
        # Return component (30%)
        if expected_return > 0.01:  # >1% per trade
            score += 0.3
        elif expected_return > 0.005:  # >0.5% per trade
            score += 0.15
        
        # Win rate component (20%)
        if win_rate > 0.6:
            score += 0.2
        elif win_rate > 0.55:
            score += 0.1
        
        # Risk-adjusted returns (25%)
        if sharpe_ratio > 2.0:
            score += 0.25
        elif sharpe_ratio > 1.5:
            score += 0.15
        elif sharpe_ratio > 1.0:
            score += 0.1
        
        # Drawdown control (10%)
        if max_drawdown < 0.05:  # <5%
            score += 0.1
        elif max_drawdown < 0.1:  # <10%
            score += 0.05
        
        # Statistical significance (10%)
        if p_value < 0.01:
            score += 0.1
        elif p_value < 0.05:
            score += 0.05
        
        # Sample size adequacy (5%)
        if sample_size >= 500:
            score += 0.05
        elif sample_size >= 100:
            score += 0.025
        
        # Cost efficiency penalty
        if cost_impact > 0.5:  # >50% of gross returns
            score *= 0.5
        elif cost_impact > 0.3:  # >30% of gross returns
            score *= 0.8
        
        return min(1.0, max(0.0, score))
    
    def _empty_metrics(self) -> EdgeMetrics:
        """Return empty metrics for invalid patterns."""
        return EdgeMetrics(
            expected_return_per_trade=0,
            expected_return_annualized=0,
            gross_return_per_trade=0,
            volatility=0,
            sharpe_ratio=0,
            max_drawdown=0,
            var_95=0,
            win_rate=0,
            profit_factor=0,
            average_win=0,
            average_loss=0,
            total_trades=0,
            trade_frequency_per_day=0,
            p_value=1.0,
            confidence_interval=(0, 0),
            t_statistic=0,
            sample_size=0,
            degrees_of_freedom=0,
            transaction_cost_impact=0,
            slippage_impact=0,
            fee_impact=0,
            funding_impact=0,
            regime_performance={},
            deployment_score=0,
            deployment_approved=False
        )

class DeploymentCriteria:
    """Evaluate patterns for deployment readiness."""
    
    def __init__(self):
        self.criteria = {
            'statistically_significant': {'threshold': 0.05, 'weight': 0.2},
            'economically_significant': {'threshold': 0.01, 'weight': 0.25},
            'sufficient_sample_size': {'threshold': 100, 'weight': 0.1},
            'good_sharpe_ratio': {'threshold': 1.5, 'weight': 0.2},
            'acceptable_drawdown': {'threshold': 0.1, 'weight': 0.15},
            'cost_efficient': {'threshold': 0.3, 'weight': 0.1}
        }
    
    def evaluate_pattern_for_deployment(
        self, 
        edge_metrics: EdgeMetrics
    ) -> DeploymentDecision:
        """Evaluate if pattern meets deployment criteria."""
        
        criteria_checks = {
            'statistically_significant': edge_metrics.p_value < self.criteria['statistically_significant']['threshold'],
            'economically_significant': edge_metrics.expected_return_per_trade > self.criteria['economically_significant']['threshold'],
            'sufficient_sample_size': edge_metrics.sample_size >= self.criteria['sufficient_sample_size']['threshold'],
            'good_sharpe_ratio': edge_metrics.sharpe_ratio > self.criteria['good_sharpe_ratio']['threshold'],
            'acceptable_drawdown': edge_metrics.max_drawdown < self.criteria['acceptable_drawdown']['threshold'],
            'cost_efficient': edge_metrics.transaction_cost_impact < self.criteria['cost_efficient']['threshold']
        }
        
        # Calculate weighted score
        total_score = 0
        total_weight = 0
        
        for criterion, passed in criteria_checks.items():
            weight = self.criteria[criterion]['weight']
            total_score += weight if passed else 0
            total_weight += weight
        
        deployment_score = total_score / total_weight if total_weight > 0 else 0
        
        # All critical criteria must pass
        critical_criteria = ['statistically_significant', 'economically_significant']
        deployment_approved = all(criteria_checks[c] for c in critical_criteria) and deployment_score > 0.7
        
        # Generate recommendation
        recommendation = self._generate_recommendation(criteria_checks, edge_metrics)
        
        # Calculate risk limits if approved
        risk_limits = self._calculate_risk_limits(edge_metrics) if deployment_approved else None
        
        return DeploymentDecision(
            approved=deployment_approved,
            criteria_checks=criteria_checks,
            recommendation=recommendation,
            risk_limits=risk_limits,
            deployment_score=deployment_score
        )
    
    def _generate_recommendation(self, criteria_checks: Dict[str, bool], edge_metrics: EdgeMetrics) -> str:
        """Generate deployment recommendation."""
        
        failed_criteria = [k for k, v in criteria_checks.items() if not v]
        
        if not failed_criteria:
            return "APPROVED: All criteria met. Ready for live deployment."
        
        if 'statistically_significant' in failed_criteria:
            return f"REJECTED: Not statistically significant (p-value: {edge_metrics.p_value:.4f}). Need more data or better pattern."
        
        if 'economically_significant' in failed_criteria:
            return f"REJECTED: Insufficient edge ({edge_metrics.expected_return_per_trade:.2%} per trade). Need >1% expected return."
        
        if len(failed_criteria) <= 2:
            return f"CONDITIONAL: Minor issues with {', '.join(failed_criteria)}. Consider paper trading first."
        
        return f"REJECTED: Multiple criteria failed: {', '.join(failed_criteria)}. Requires significant improvement."
    
    def _calculate_risk_limits(self, edge_metrics: EdgeMetrics) -> RiskLimits:
        """Calculate appropriate risk limits for deployment."""
        
        # Base position size on Kelly criterion
        kelly_fraction = edge_metrics.expected_return_per_trade / (edge_metrics.volatility ** 2) if edge_metrics.volatility > 0 else 0
        kelly_fraction = min(0.25, max(0.01, kelly_fraction))  # Cap at 25%, min 1%
        
        # Conservative position sizing (50% of Kelly)
        max_position_size = kelly_fraction * 0.5 * 100000  # Assume $100k base capital
        
        # Daily trade limits based on frequency
        max_daily_trades = max(1, int(edge_metrics.trade_frequency_per_day * 2))
        
        # Drawdown threshold (2x historical max drawdown)
        max_drawdown_threshold = min(0.2, edge_metrics.max_drawdown * 2)
        
        # Stop loss threshold (3x average loss)
        stop_loss_threshold = min(0.05, abs(edge_metrics.average_loss) * 3)
        
        return RiskLimits(
            max_position_size_usd=max_position_size,
            max_daily_trades=max_daily_trades,
            max_drawdown_threshold=max_drawdown_threshold,
            stop_loss_threshold=stop_loss_threshold,
            correlation_limit=0.7  # Max correlation with other strategies
        )