"""Order Persistence — ensures no ghost orders by persisting intent before submission.

Every order goes through: persist intent → submit to exchange → update status.
This prevents lost capital from orders submitted but not tracked.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("swarm.execution.persistence")


class OrderStatus(str, Enum):
    PENDING_SUBMISSION = "pending_submission"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class OrderRequest:
    """Represents an order before submission."""
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET", "LIMIT"
    quantity: float
    price: float | None = None  # Required for LIMIT orders
    strategy_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersistedOrder:
    """An order that has been persisted with tracking information."""
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None
    strategy_id: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    exchange_order_id: str | None = None
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OrderPersistence:
    """Manages order lifecycle with persistence.

    Persists order intent before submission to exchange,
    ensuring complete audit trail and preventing ghost orders.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._orders: dict[str, PersistedOrder] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _generate_client_order_id() -> str:
        """Generate a unique client order ID."""
        ts = str(int(time.time()))
        unique = uuid.uuid4().hex[:8]
        return f"cs_{ts}_{unique}"

    async def persist_order_intent(self, order: OrderRequest) -> str:
        """Record the order intent before submitting it to the exchange.

        Args:
            order: The order request to persist.

        Returns:
            The generated client_order_id for tracking.
        """
        client_order_id = self._generate_client_order_id()
        now = datetime.now(timezone.utc)

        persisted = PersistedOrder(
            client_order_id=client_order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            strategy_id=order.strategy_id,
            status=OrderStatus.PENDING_SUBMISSION,
            created_at=now,
            updated_at=now,
            metadata=order.metadata,
        )

        async with self._lock:
            self._orders[client_order_id] = persisted

            if self._db is not None:
                try:
                    await self._db.write_order_intent({
                        "client_order_id": client_order_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "order_type": order.order_type,
                        "quantity": order.quantity,
                        "price": order.price,
                        "strategy_id": order.strategy_id,
                        "status": OrderStatus.PENDING_SUBMISSION.value,
                        "timestamp": now.isoformat(),
                    })
                except Exception as exc:
                    logger.error("Failed to persist order to DB: %s", exc)

        logger.info(
            "Order intent persisted: %s %s %s %.6f @ %s",
            client_order_id, order.side, order.symbol,
            order.quantity, order.price or "MARKET",
        )
        return client_order_id

    async def persist_from_position(
        self,
        position: Any,
        strategy_id: str = "",
    ) -> str:
        """Convenience: persist intent from a PositionManager Position object.

        Converts the Position dataclass into an OrderRequest before persisting.

        Args:
            position: A Position from the PositionManager.
            strategy_id: Strategy ID override (falls back to position.strategy_id).

        Returns:
            The generated client_order_id.
        """
        raw_side = getattr(position, "side", "BUY")
        # PositionSide enum → string
        side_str: str = raw_side.value if hasattr(raw_side, "value") else str(raw_side)

        order = OrderRequest(
            symbol=position.symbol,
            side=side_str,
            order_type="MARKET",
            quantity=float(getattr(position, "size_tokens", 0.0)),
            price=float(getattr(position, "entry_price", 0.0)) or None,
            strategy_id=strategy_id or getattr(position, "strategy_id", ""),
            metadata={
                "position_id": getattr(position, "position_id", ""),
                "size_usd": getattr(position, "size_usd", 0.0),
                "stop_loss": getattr(position, "stop_loss_price", None),
                "take_profit": getattr(position, "take_profit_price", None),
            },
        )
        return await self.persist_order_intent(order)

    async def update_status(
        self,
        client_order_id: str,
        status: OrderStatus,
        *,
        exchange_order_id: str | None = None,
        filled_quantity: float | None = None,
        filled_price: float | None = None,
        error_message: str | None = None,
    ) -> PersistedOrder | None:
        """Update the status of a persisted order."""
        async with self._lock:
            order = self._orders.get(client_order_id)
            if order is None:
                logger.warning("Order %s not found", client_order_id)
                return None

            order.status = status
            order.updated_at = datetime.now(timezone.utc)
            if exchange_order_id is not None:
                order.exchange_order_id = exchange_order_id
            if filled_quantity is not None:
                order.filled_quantity = filled_quantity
            if filled_price is not None:
                order.filled_price = filled_price
            if error_message is not None:
                order.error_message = error_message

            logger.info(
                "Order %s status → %s", client_order_id, status.value,
            )
            return order

    async def get_pending_orders(self) -> list[PersistedOrder]:
        """Get all orders with PENDING_SUBMISSION or SUBMITTED status."""
        async with self._lock:
            return [
                o for o in self._orders.values()
                if o.status in (OrderStatus.PENDING_SUBMISSION, OrderStatus.SUBMITTED)
            ]

    async def get_order(self, client_order_id: str) -> PersistedOrder | None:
        """Retrieve a specific order by ID."""
        return self._orders.get(client_order_id)

    async def get_stale_orders(self, age_seconds: float = 300) -> list[PersistedOrder]:
        """Get orders that have been PENDING_SUBMISSION for too long."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            return [
                o for o in self._orders.values()
                if o.status == OrderStatus.PENDING_SUBMISSION
                and (now - o.created_at).total_seconds() > age_seconds
            ]

    async def get_all_orders(self) -> list[PersistedOrder]:
        """Return all persisted orders (for dashboard/API)."""
        async with self._lock:
            return list(self._orders.values())

    def get_order_stats(self) -> dict[str, Any]:
        """Return summary statistics for all persisted orders."""
        total = len(self._orders)
        by_status: dict[str, int] = {}
        for o in self._orders.values():
            status_key = o.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

        return {
            "total_orders": total,
            "by_status": by_status,
            "pending_count": by_status.get("pending_submission", 0) + by_status.get("submitted", 0),
            "filled_count": by_status.get("filled", 0),
            "failed_count": by_status.get("failed", 0) + by_status.get("rejected", 0),
        }
