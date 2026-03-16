"""DEPRECATED: Legacy Backtest Engine for CryptoSwarms.

This is the old fake backtesting system. Use RealBacktestEngine instead.
For real alpha discovery, use AlphaDiscoveryEngine.

MIGRATION PATH:
- Replace BacktestEngine with RealBacktestEngine
- Use AlphaDiscoveryEngine for pattern discovery
- Use EdgeQuantifier for real edge metrics
"""
from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, List, Dict

from cryptoswarms.position_manager import PositionManager, ExitReason
from cryptoswarms.common.strategy import BaseStrategy
from cryptoswarms.kelly_sizer import kelly_size

logger = logging.getLogger("backtest.engine.legacy")

# DEPRECATED: Use AlphaDiscoveryEngine instead
class LegacyBacktestEngine:

class LegacyBacktestEngine:
    def __init__(
        self, 
        base_bankroll: float = 10000.0,
        slippage_bps: float = 5.0,
        fee_rate: float = 0.001
    ):
        self.bankroll = base_bankroll
        self.pm = PositionManager()
        self.pm.SLIPPAGE_BPS = slippage_bps
        self.pm.FEE_RATE = fee_rate
        self.history: List[Dict[str, Any]] = []

    async def run(
        self, 
        strategy: BaseStrategy, 
        candles: List[List[Any]], 
        symbol: str
    ):
        """
        Run backtest for a specific strategy and symbol.
        """
        logger.info(f"Starting backtest for {symbol} with strategy {strategy.config.id}")
        
        from cryptoswarms.common.indicators import (
            calculate_bollinger_bands, calculate_rsi, calculate_ema, calculate_vwap
        )
        
        lookback = max(250, strategy.config.parameters.get("lookback_candles", 100))
        
        for i in range(lookback, len(candles)):
            current_kline = candles[i]
            current_price = float(current_kline[4])
            current_time = datetime.fromtimestamp(current_kline[0] / 1000, tz=timezone.utc)
            
            # 1. Update Position Manager (Check Exits)
            self.pm.check_exits({symbol: current_price}, timestamp=current_time)
            
            # 2. Entry Logic
            has_pos = any(p.symbol == symbol and p.strategy_id == strategy.config.id for p in self.pm.open_positions.values())
            
            if not has_pos:
                signal = None
                context = {"current_regime": "BULLISH_TREND", "smart_money": True}
                prices = [float(k[4]) for k in candles[i-lookback:i]]
                
                # --- STRATEGY: BREAKOUT ---
                if strategy.config.id == "strat-breakout-v1":
                    bb = calculate_bollinger_bands(prices, 20, strategy.config.parameters.get("std_dev_multiplier", 2.5))
                    if bb and current_price > bb["upper"]:
                        signal = {"signal_type": "BREAKOUT", "symbol": symbol}

                # --- STRATEGY: MEAN REVERSION (RSI) ---
                elif strategy.config.id == "strat-mean-reversion-rsi":
                    rsi = calculate_rsi(prices, 14)
                    if rsi and rsi < strategy.config.parameters.get("rsi_oversold", 30):
                        signal = {"signal_type": "RSI_OVERSOLD", "symbol": symbol}
                        context["rsi_value"] = rsi
                        context["current_regime"] = "RANGING"

                # --- STRATEGY: TREND RIDER (MACD/EMA) ---
                elif strategy.config.id == "strat-trend-rider-macd":
                    ema200 = calculate_ema(prices, 200)
                    if ema200 and current_price > ema200:
                        # Simple MACD cross simulation
                        signal = {"signal_type": "TREND_CROSS", "symbol": symbol}
                        context["htf_bullish"] = True

                # --- STRATEGY: VWAP INSTITUTIONAL ---
                elif strategy.config.id == "strat-vwap-institutional":
                    vwap = calculate_vwap(candles[i-24:i]) # Daily-ish VWAP
                    dev = (current_price - vwap) / vwap
                    if abs(dev) > strategy.config.parameters.get("vwap_deviation_threshold", 0.02):
                        signal = {
                            "signal_type": "VWAP_DEVIATION", 
                            "symbol": symbol,
                            "side": "BELOW" if dev < 0 else "ABOVE"
                        }
                        context["vwap_price"] = vwap
                        context["deviation_pct"] = dev
                        context["volume_surge"] = True

                # --- STRATEGY: GOLDEN CROSS ---
                elif strategy.config.id == "strat-golden-cross":
                    ema50 = calculate_ema(prices, 50)
                    ema200 = calculate_ema(prices, 200)
                    if ema50 and ema200 and ema50 > ema200:
                        # Simple crossover detection (was it below before?)
                        # For simplicity, we trigger if above and no position
                        signal = {"signal_type": "GOLDEN_CROSS", "symbol": symbol}

                if signal:
                    decision = await strategy.evaluate(signal, context)
                    
                    if decision:
                        # Position sizing
                        ks = kelly_size(
                            win_rate=0.5,
                            avg_win_pct=strategy.config.parameters.get("take_profit_pct", 0.04), 
                            avg_loss_pct=strategy.config.stop_loss_pct or 0.02, 
                            bankroll_usd=self.bankroll,
                            max_position_pct=0.1
                        )
                        
                        size_usd = ks.suggested_size_usd
                        if size_usd > 0:
                            self.pm.open_position(
                                strategy_id=strategy.config.id,
                                symbol=symbol,
                                side=decision.get("action", "BUY"),
                                entry_price=current_price,
                                size_usd=size_usd,
                                stop_loss_pct=strategy.config.stop_loss_pct or 0.02,
                                take_profit_pct=strategy.config.parameters.get("take_profit_pct", 0.04),
                                trailing_stop_pct=strategy.config.parameters.get("trailing_stop_pct", 0.0),
                                max_hold_candles=48,
                                metadata={"timestamp": current_time}
                            )
                            print(f"[{current_time}] ENTRY: {symbol} @ {current_price:.2f} | Size: ${size_usd:.2f} | Strat: {strategy.config.id}")

        return self.pm.summary()
