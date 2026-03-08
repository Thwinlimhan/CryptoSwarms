from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Protocol

from cryptoswarms.macro_calendar import MacroEvent, in_macro_blackout
from cryptoswarms.trade_attribution import TradeAttribution, TradeAttributionError, attribution_payload


class GateCheckError(RuntimeError):
    """Raised when execution gate checks fail."""


class ConfirmGateError(GateCheckError):
    """Raised when CONFIRM gate verification fails."""


class ExchangeExecutionError(RuntimeError):
    """Raised when an exchange adapter cannot execute an order."""


class ExchangeAdapter(Protocol):
    """Exchange adapter interface with explicit paper/live execution modes."""

    name: str
    mode: str

    def place_order(self, order: "OrderRequest") -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_price: Optional[float] = None


@dataclass
class TradeSignal:
    signal_id: str
    symbol: str
    side: str
    quantity: float
    confidence: float
    timestamp: datetime
    gate_passed: bool


@dataclass
class RiskSnapshot:
    heartbeat_ts: datetime
    drawdown_pct: float
    heat_pct: float
    halt_active: bool
    reason: Optional[str] = None


class CircuitLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


@dataclass(frozen=True)
class ExecutionConfig:
    min_confidence: float = 0.70
    max_signal_age: timedelta = timedelta(minutes=5)
    max_heartbeat_age: timedelta = timedelta(minutes=10)
    max_drawdown_pct: float = 8.0
    max_heat_pct: float = 25.0
    macro_blackout_minutes: int = 30
    macro_events_utc: tuple[MacroEvent, ...] = ()
    paperclip_guard: object | None = None


class EventPublisher(Protocol):
    def publish(self, channel: str, payload: Dict[str, Any]) -> None:
        ...


class ConfirmGate(Protocol):
    def verify(self, token: str, action_record_id: str) -> bool:
        ...


class BaseExchangeAdapter:
    """Shared enforcement for mandatory stop-loss and take-profit checks."""

    def __init__(self, *, name: str, mode: str = "paper") -> None:
        if mode not in {"paper", "live"}:
            raise ValueError("mode must be either 'paper' or 'live'")
        self.name = name
        self.mode = mode

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        self._validate_order(order, mode=self.mode)
        return {
            "exchange": self.name,
            "mode": self.mode,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "status": "filled" if self.mode == "paper" else "accepted",
        }

    @staticmethod
    def _validate_order(order: OrderRequest, mode: str) -> None:
        if order.stop_loss is None or order.take_profit is None:
            raise ExchangeExecutionError("stop_loss and take_profit are mandatory")
        if order.quantity <= 0:
            raise ExchangeExecutionError("quantity must be positive")

        if mode == "live" and order.entry_price is not None:
            side = order.side.lower()
            if side == "buy":
                if not (order.stop_loss < order.entry_price < order.take_profit):
                    raise ExchangeExecutionError("invalid live long risk bounds")
            elif side == "sell":
                if not (order.take_profit < order.entry_price < order.stop_loss):
                    raise ExchangeExecutionError("invalid live short risk bounds")
            else:
                raise ExchangeExecutionError("unsupported side")


class BinanceExchangeAdapter(BaseExchangeAdapter):
    def __init__(self, mode: str = "paper") -> None:
        super().__init__(name="binance", mode=mode)


class HyperliquidExchangeAdapter(BaseExchangeAdapter):
    def __init__(self, mode: str = "paper") -> None:
        super().__init__(name="hyperliquid", mode=mode)


class AsterExchangeAdapter(BaseExchangeAdapter):
    def __init__(self, mode: str = "paper") -> None:
        super().__init__(name="aster", mode=mode)


class OkxExchangeAdapter(BaseExchangeAdapter):
    def __init__(self, mode: str = "paper") -> None:
        super().__init__(name="okx", mode=mode)


class ExecutionAgent:
    def __init__(
        self,
        *,
        exchange_adapter: ExchangeAdapter,
        event_publisher: EventPublisher,
        confirm_gate: ConfirmGate,
        config: Optional[ExecutionConfig] = None,
    ) -> None:
        self.exchange_adapter = exchange_adapter
        self.event_publisher = event_publisher
        self.confirm_gate = confirm_gate
        self.config = config or ExecutionConfig()

    def execute(
        self,
        *,
        signal: TradeSignal,
        risk: RiskSnapshot,
        confirm_token: str,
        action_record_id: str,
        stop_loss: float,
        take_profit: float,
        entry_price: float | None = None,
        estimated_llm_cost_usd: float = 0.0,
        now: Optional[datetime] = None,
        attribution: TradeAttribution | None = None,
    ) -> Dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        self._enforce_pre_trade_checklist(signal=signal, risk=risk, now=now)
        self._enforce_paperclip(estimated_llm_cost_usd=estimated_llm_cost_usd)
        self._verify_confirm_gate(confirm_token=confirm_token, action_record_id=action_record_id)

        if self.exchange_adapter.mode == "live":
            self._enforce_live_attribution(attribution=attribution, signal_id=signal.signal_id)

        order = OrderRequest(
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_price=entry_price,
        )
        response = self.exchange_adapter.place_order(order)

        if attribution is not None:
            response["attribution"] = attribution_payload(attribution)
        response["signal_id"] = signal.signal_id
        response["action_record_id"] = action_record_id
        return response

    def _enforce_live_attribution(self, *, attribution: TradeAttribution | None, signal_id: str) -> None:
        if attribution is None:
            self.event_publisher.publish(
                "execution:blocked",
                {
                    "reason": "missing_live_trade_attribution",
                    "signal_id": signal_id,
                },
            )
            raise GateCheckError("live execution requires trade attribution")
        try:
            attribution_payload(attribution)
        except TradeAttributionError as exc:
            self.event_publisher.publish(
                "execution:blocked",
                {
                    "reason": "invalid_live_trade_attribution",
                    "signal_id": signal_id,
                    "details": str(exc),
                },
            )
            raise GateCheckError(f"invalid trade attribution: {exc}") from exc

    def _enforce_paperclip(self, *, estimated_llm_cost_usd: float) -> None:
        guard = self.config.paperclip_guard
        if guard is None:
            return

        decision = guard.check(
            estimated_increment_usd=estimated_llm_cost_usd,
            action="execute_order",
            actor="execution_agent",
        )
        if not decision.allowed:
            self.event_publisher.publish(
                "execution:blocked",
                {"reason": decision.reason, "projected_spend_usd": decision.projected_spend_usd},
            )
            raise GateCheckError(f"Paperclip blocked execution: {decision.reason}")

    def _verify_confirm_gate(self, *, confirm_token: str, action_record_id: str) -> None:
        if not self.confirm_gate.verify(confirm_token, action_record_id):
            self.event_publisher.publish(
                "execution:blocked",
                {"reason": "confirm_gate_failed", "action_record_id": action_record_id},
            )
            raise ConfirmGateError("CONFIRM gate verification failed")

    def _enforce_pre_trade_checklist(
        self,
        *,
        signal: TradeSignal,
        risk: RiskSnapshot,
        now: datetime,
    ) -> None:
        failures = []
        if signal.confidence < self.config.min_confidence:
            failures.append("confidence")
        if now - signal.timestamp > self.config.max_signal_age:
            failures.append("signal_freshness")
        if not signal.gate_passed:
            failures.append("gate_pass_status")
        if now - risk.heartbeat_ts > self.config.max_heartbeat_age:
            failures.append("heartbeat_freshness")
        if risk.drawdown_pct > self.config.max_drawdown_pct:
            failures.append("drawdown_limit")
        if risk.heat_pct > self.config.max_heat_pct:
            failures.append("heat_limit")
        if risk.halt_active:
            failures.append("risk_halt")

        macro_blocked, event_name = in_macro_blackout(
            now,
            self.config.macro_events_utc,
            window_minutes=self.config.macro_blackout_minutes,
        )
        if macro_blocked:
            failures.append(f"macro_blackout:{event_name}")

        if failures:
            self.event_publisher.publish(
                "execution:blocked",
                {
                    "reason": "pre_trade_checklist_failed",
                    "failures": failures,
                    "signal_id": signal.signal_id,
                },
            )
            raise GateCheckError(f"Pre-trade checklist failed: {', '.join(failures)}")
