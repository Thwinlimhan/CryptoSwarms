"""Position Manager — tracks all open and closed positions.

This is the core state machine that knows what the swarm currently holds.
Every entry, exit, stop-loss, and take-profit flows through here.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("swarm.positions")


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TIME_EXIT = "time_exit"
    REGIME_CHANGE = "regime_change"
    MANUAL = "manual"
    SIGNAL_REVERSE = "signal_reverse"


@dataclass
class Position:
    position_id: str
    strategy_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    size_usd: float
    size_tokens: float
    entry_time: datetime
    stop_loss_price: float
    take_profit_price: float
    max_hold_candles: int = 20       # Force exit after N candles
    candles_held: int = 0
    trailing_stop_pct: float = 0.0   # 0 = disabled
    highest_price: float = 0.0       # For trailing stop (longs)
    lowest_price: float = 999999.0   # For trailing stop (shorts)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized PnL based on highest/lowest tracked price."""
        ref = self.highest_price if self.side == PositionSide.LONG else self.lowest_price
        if self.side == PositionSide.LONG:
            return (ref - self.entry_price) / self.entry_price * self.size_usd
        else:
            return (self.entry_price - ref) / self.entry_price * self.size_usd


@dataclass(frozen=True)
class ClosedTrade:
    trade_id: str
    position_id: str
    strategy_id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size_usd: float
    size_tokens: float
    entry_time: datetime
    exit_time: datetime
    pnl_usd: float
    pnl_pct: float
    fees_usd: float
    slippage_bps: float
    exit_reason: str
    hold_duration_seconds: int
    metadata: dict[str, Any] = field(default_factory=dict)


class PositionManager:
    """Tracks all open positions and manages exits."""

    # Constants
    FEE_RATE = 0.001          # 0.1% round-trip
    SLIPPAGE_BPS = 5.0        # 5 bps per side

    def __init__(self) -> None:
        self.open_positions: dict[str, Position] = {}
        self.closed_trades: list[ClosedTrade] = []

    # ── Entry ─────────────────────────────────────────────────────
    def open_position(
        self,
        *,
        strategy_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        size_usd: float,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
        max_hold_candles: int = 20,
        trailing_stop_pct: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Open a new tracked position."""
        # Prevent duplicate positions in the same symbol+strategy
        for pos in self.open_positions.values():
            if pos.symbol == symbol and pos.strategy_id == strategy_id:
                logger.warning("Already have position in %s for %s", symbol, strategy_id)
                return pos

        pos_side = PositionSide.LONG if side.upper() in ("BUY", "LONG") else PositionSide.SHORT
        size_tokens = size_usd / entry_price

        # Calculate stop-loss and take-profit prices
        if pos_side == PositionSide.LONG:
            sl_price = entry_price * (1 - stop_loss_pct)
            tp_price = entry_price * (1 + take_profit_pct)
        else:
            sl_price = entry_price * (1 + stop_loss_pct)
            tp_price = entry_price * (1 - take_profit_pct)

        position = Position(
            position_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            symbol=symbol,
            side=pos_side,
            entry_price=entry_price,
            size_usd=size_usd,
            size_tokens=size_tokens,
            entry_time=(metadata or {}).get("timestamp") or datetime.now(timezone.utc),
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            max_hold_candles=max_hold_candles,
            trailing_stop_pct=trailing_stop_pct,
            highest_price=entry_price,
            lowest_price=entry_price,
            metadata=metadata or {},
        )
        self.open_positions[position.position_id] = position
        return position

    # ── Exit ──────────────────────────────────────────────────────
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: ExitReason,
        timestamp: datetime | None = None,
        slippage_bps: float | None = None,
    ) -> ClosedTrade | None:
        """Close an open position and record the trade."""
        pos = self.open_positions.pop(position_id, None)
        if not pos:
            return None

        now = timestamp or datetime.now(timezone.utc)
        actual_slippage = slippage_bps if slippage_bps is not None else self.SLIPPAGE_BPS

        # Apply slippage to exit price
        slip_mult = actual_slippage / 10000
        if pos.side == PositionSide.LONG:
            adjusted_exit = exit_price * (1 - slip_mult)  # Sell lower
        else:
            adjusted_exit = exit_price * (1 + slip_mult)  # Buy back higher

        # Calculate PnL
        if pos.side == PositionSide.LONG:
            pnl_pct = (adjusted_exit - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - adjusted_exit) / pos.entry_price

        fees = pos.size_usd * self.FEE_RATE
        gross_pnl = pnl_pct * pos.size_usd
        net_pnl = gross_pnl - fees

        trade = ClosedTrade(
            trade_id=str(uuid.uuid4())[:12],
            position_id=position_id,
            strategy_id=pos.strategy_id,
            symbol=pos.symbol,
            side=pos.side.value,
            entry_price=pos.entry_price,
            exit_price=adjusted_exit,
            size_usd=pos.size_usd,
            size_tokens=pos.size_tokens,
            entry_time=pos.entry_time,
            exit_time=now,
            pnl_usd=round(net_pnl, 2),
            pnl_pct=round(pnl_pct * 100, 4),
            fees_usd=round(fees, 2),
            slippage_bps=actual_slippage,
            exit_reason=exit_reason.value,
            hold_duration_seconds=int((now - pos.entry_time).total_seconds()),
            metadata=pos.metadata,
        )
        self.closed_trades.append(trade)
        logger.info(
            "CLOSED %s %s @ %.4f | PnL=$%.2f (%.2f%%) | Reason=%s",
            pos.side.value, pos.symbol, adjusted_exit, net_pnl, pnl_pct * 100, exit_reason.value
        )
        return trade

    # ── Check Exits ───────────────────────────────────────────────
    def check_exits(self, current_prices: dict[str, float], timestamp: datetime | None = None) -> list[ClosedTrade]:
        """Check all open positions for stop-loss, take-profit, or time exit."""
        closed: list[ClosedTrade] = []
        positions_to_check = list(self.open_positions.values())

        for pos in positions_to_check:
            price = current_prices.get(pos.symbol)
            if price is None:
                continue

            pos.highest_price = max(pos.highest_price, price)
            pos.lowest_price = min(pos.lowest_price, price)
            pos.candles_held += 1

            # Update trailing stop if enabled
            if pos.trailing_stop_pct > 0:
                if pos.side == PositionSide.LONG:
                    new_sl = pos.highest_price * (1 - pos.trailing_stop_pct)
                    if new_sl > pos.stop_loss_price:
                        pos.stop_loss_price = new_sl
                else:
                    new_sl = pos.lowest_price * (1 + pos.trailing_stop_pct)
                    if new_sl < pos.stop_loss_price:
                        pos.stop_loss_price = new_sl

            exit_reason = None
            if pos.side == PositionSide.LONG and price <= pos.stop_loss_price:
                exit_reason = ExitReason.STOP_LOSS
            elif pos.side == PositionSide.SHORT and price >= pos.stop_loss_price:
                exit_reason = ExitReason.STOP_LOSS
            elif pos.side == PositionSide.LONG and price >= pos.take_profit_price:
                exit_reason = ExitReason.TAKE_PROFIT
            elif pos.side == PositionSide.SHORT and price <= pos.take_profit_price:
                exit_reason = ExitReason.TAKE_PROFIT
            elif pos.candles_held >= pos.max_hold_candles:
                exit_reason = ExitReason.TIME_EXIT

            if exit_reason:
                trade = self.close_position(pos.position_id, price, exit_reason, timestamp=timestamp)
                if trade:
                    closed.append(trade)

        return closed

    # ── Portfolio Metrics ─────────────────────────────────────────
    @property
    def portfolio_heat(self) -> float:
        """Total USD at risk across all open positions."""
        return sum(p.size_usd for p in self.open_positions.values())

    @property
    def total_pnl(self) -> float:
        """Total realized PnL across all closed trades."""
        return sum(t.pnl_usd for t in self.closed_trades)

    @property
    def win_rate(self) -> float:
        """Win rate as a decimal (0.0 to 1.0)."""
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t.pnl_usd > 0)
        return wins / len(self.closed_trades)

    @property
    def profit_factor(self) -> float:
        """Gross profit / gross loss. >1.0 means net profitable."""
        gross_profit = sum(t.pnl_usd for t in self.closed_trades if t.pnl_usd > 0)
        gross_loss = abs(sum(t.pnl_usd for t in self.closed_trades if t.pnl_usd < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def summary(self) -> dict[str, Any]:
        """Return a summary of all trading performance."""
        if not self.closed_trades:
            return {"trades": 0, "message": "No closed trades yet"}

        pnls = [t.pnl_usd for t in self.closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        return {
            "total_trades": len(self.closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": f"{self.win_rate * 100:.1f}%",
            "total_pnl": f"${self.total_pnl:.2f}",
            "avg_win": f"${sum(wins) / len(wins):.2f}" if wins else "$0",
            "avg_loss": f"${sum(losses) / len(losses):.2f}" if losses else "$0",
            "biggest_win": f"${max(pnls):.2f}",
            "biggest_loss": f"${min(pnls):.2f}",
            "profit_factor": f"{self.profit_factor:.2f}",
            "open_positions": len(self.open_positions),
            "portfolio_heat": f"${self.portfolio_heat:.2f}",
        }
