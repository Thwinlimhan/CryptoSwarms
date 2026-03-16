"""Real Backtesting Engine for CryptoSwarms.

Replaces fake backtesting with realistic trade simulation including
proper transaction costs, slippage, and market impact modeling.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

logger = logging.getLogger("cryptoswarms.backtest.real")

@dataclass
class Trade:
    """Represents a completed trade with all costs."""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size_usd: float
    direction: str  # "long" or "short"
    pnl_gross: float
    pnl_net: float
    fees: float
    slippage: float
    market_impact: float
    funding_cost: float
    exit_reason: str

@dataclass
class BacktestResult:
    """Complete backtest results."""
    pattern_name: str
    symbol: str
    interval: str
    period: tuple[datetime, datetime]
    trades: List[Trade]
    performance: 'PerformanceMetrics'
    risk_metrics: 'RiskMetrics'
    transaction_cost_impact: float

@dataclass
class PerformanceMetrics:
    """Performance metrics for backtest."""
    total_return: float
    annualized_return: float
    expected_return_per_trade: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    sortino_ratio: float

@dataclass
class RiskMetrics:
    """Risk metrics for backtest."""
    max_drawdown: float
    volatility: float
    var_95: float
    expected_shortfall: float
    calmar_ratio: float
class RealBacktestEngine:
    """Real backtesting engine with proper cost modeling."""
    
    def __init__(self, data_warehouse, transaction_costs=None):
        self.data_warehouse = data_warehouse
        from cryptoswarms.edge.edge_quantifier import TransactionCosts
        self.transaction_costs = transaction_costs or TransactionCosts()
        
    def backtest_pattern(
        self, 
        pattern: Any, 
        symbol: str, 
        interval: str,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """Run comprehensive backtest with realistic execution."""
        
        logger.info(f"Running backtest for {pattern.pattern_name} on {symbol}")
        
        # Get historical data
        data = self.data_warehouse.query_data(symbol, interval, start_date, end_date)
        if data.empty:
            raise ValueError(f"No data available for {symbol} {interval}")
        
        # Generate signals
        signals = pattern.generate_signals(data, **pattern.optimal_parameters)
        
        if not signals:
            logger.warning(f"No signals generated for {pattern.pattern_name}")
            return self._empty_backtest_result(pattern.pattern_name, symbol, interval, (start_date, end_date))
        
        # Simulate trades
        trades = self._simulate_trades(signals, data)
        
        # Calculate performance metrics
        performance = self._calculate_performance_metrics(trades)
        risk_metrics = self._calculate_risk_metrics(trades)
        
        # Transaction cost impact
        if trades:
            gross_pnl = sum(t.pnl_gross for t in trades)
            net_pnl = sum(t.pnl_net for t in trades)
            cost_impact = abs(gross_pnl - net_pnl) / abs(gross_pnl) if gross_pnl != 0 else 0
        else:
            cost_impact = 0
        
        return BacktestResult(
            pattern_name=pattern.pattern_name,
            symbol=symbol,
            interval=interval,
            period=(start_date, end_date),
            trades=trades,
            performance=performance,
            risk_metrics=risk_metrics,
            transaction_cost_impact=cost_impact
        )
    def _simulate_trades(self, signals: List[Any], data: pd.DataFrame) -> List[Trade]:
        """Simulate realistic trade execution."""
        
        trades = []
        
        for signal in signals:
            try:
                trade = self._simulate_single_trade(signal, data)
                if trade:
                    trades.append(trade)
            except Exception as e:
                logger.warning(f"Error simulating trade: {e}")
                continue
        
        return trades
    
    def _simulate_single_trade(self, signal: Any, data: pd.DataFrame) -> Optional[Trade]:
        """Simulate a single trade with realistic costs."""
        
        # Find signal in data
        signal_data = data[data['timestamp'] == signal.timestamp]
        if len(signal_data) == 0:
            return None
        
        signal_idx = signal_data.index[0]
        entry_price = signal.price
        
        # Position size (simplified - use fixed $1000 per trade)
        size_usd = 1000.0
        
        # Entry execution with costs
        entry_slippage = self._calculate_slippage(entry_price, size_usd, 'entry')
        entry_fee = size_usd * self.transaction_costs.taker_fee
        market_impact = self._calculate_market_impact(size_usd, entry_price)
        
        actual_entry_price = entry_price + entry_slippage + market_impact
        
        # Trade management parameters
        take_profit_pct = 0.02  # 2%
        stop_loss_pct = 0.01    # 1%
        max_hold_periods = 48   # Max holding time
        
        # Look for exit
        exit_info = self._find_exit(
            data, signal_idx, actual_entry_price, signal.direction,
            take_profit_pct, stop_loss_pct, max_hold_periods
        )
        
        if not exit_info:
            return None
        
        exit_price, exit_time, exit_reason, hold_periods = exit_info
        
        # Exit execution with costs
        exit_slippage = self._calculate_slippage(exit_price, size_usd, 'exit')
        exit_fee = size_usd * self.transaction_costs.taker_fee
        
        actual_exit_price = exit_price - exit_slippage
        
        # Calculate PnL
        if signal.direction == 'long':
            pnl_gross = (actual_exit_price - actual_entry_price) / actual_entry_price * size_usd
        else:  # short
            pnl_gross = (actual_entry_price - actual_exit_price) / actual_entry_price * size_usd
        
        # Total costs
        total_fees = entry_fee + exit_fee
        total_slippage = entry_slippage + exit_slippage
        funding_cost = self._calculate_funding_cost(size_usd, hold_periods)
        
        total_costs = total_fees + total_slippage + market_impact + funding_cost
        pnl_net = pnl_gross - total_costs
        
        return Trade(
            entry_time=signal.timestamp,
            exit_time=exit_time,
            entry_price=actual_entry_price,
            exit_price=actual_exit_price,
            size_usd=size_usd,
            direction=signal.direction,
            pnl_gross=pnl_gross,
            pnl_net=pnl_net,
            fees=total_fees,
            slippage=total_slippage,
            market_impact=market_impact,
            funding_cost=funding_cost,
            exit_reason=exit_reason
        )