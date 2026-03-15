"""Order Reconciler — reconciles local order state with exchange state.

Periodically checks pending/submitted orders against the exchange
to ensure consistent position tracking.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.execution.reconciler")


@dataclass
class ReconciliationResult:
    """Result of a single reconciliation run."""
    timestamp: datetime
    orders_checked: int = 0
    status_updated: int = 0
    orders_missing: int = 0  # Orders in our DB but not on exchange
    orders_unknown: int = 0  # Orders on exchange but not in our DB
    errors: list[str] = field(default_factory=list)


class OrderReconciler:
    """Reconciles local order records with exchange order status.

    Runs periodically to detect and fix inconsistencies between
    the local order database and the exchange's actual order state.
    """

    def __init__(
        self,
        db: Any | None = None,
        exchange: Any | None = None,
        interval_seconds: float = 60.0,
    ) -> None:
        self._db = db
        self._exchange = exchange
        self._interval = interval_seconds
        self._running = False
        self._reconciliation_history: list[ReconciliationResult] = []
        self._task: asyncio.Task[None] | None = None

    async def reconcile_orders(self) -> ReconciliationResult:
        """Run a single reconciliation cycle.

        Checks all pending orders and updates their status
        from the exchange.
        """
        result = ReconciliationResult(timestamp=datetime.now(timezone.utc))

        try:
            # Get pending orders from DB
            if self._db is not None:
                pending_orders = await self._db.get_pending_orders()
            else:
                logger.debug("No DB configured, skipping reconciliation")
                return result

            result.orders_checked = len(pending_orders)

            for order in pending_orders:
                try:
                    order_id = getattr(order, "exchange_order_id", None) or getattr(order, "id", None)
                    if order_id is None:
                        continue

                    if self._exchange is not None:
                        exchange_status = await self._exchange.get_order_status(order_id)
                    else:
                        continue

                    local_status = getattr(order, "status", None)
                    if exchange_status != local_status:
                        await self._db.update_order_status(order_id, exchange_status)
                        result.status_updated += 1
                        logger.info(
                            "Order %s status updated: %s → %s",
                            order_id, local_status, exchange_status,
                        )
                except Exception as exc:
                    error_msg = f"Failed to reconcile order: {exc}"
                    result.errors.append(error_msg)
                    logger.warning(error_msg)

        except Exception as exc:
            error_msg = f"Reconciliation cycle failed: {exc}"
            result.errors.append(error_msg)
            logger.error(error_msg)

        self._reconciliation_history.append(result)
        # Keep last 1000 results
        if len(self._reconciliation_history) > 1000:
            self._reconciliation_history = self._reconciliation_history[-1000:]

        return result

    async def _run_loop(self) -> None:
        """Continuous reconciliation loop."""
        while self._running:
            try:
                result = await self.reconcile_orders()
                if result.status_updated > 0 or result.errors:
                    logger.info(
                        "Reconciliation: checked=%d, updated=%d, errors=%d",
                        result.orders_checked, result.status_updated,
                        len(result.errors),
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Reconciliation loop error: %s", exc)

            await asyncio.sleep(self._interval)

    async def start(self) -> None:
        """Start the reconciliation background loop."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Order reconciler started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        """Stop the reconciliation loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Order reconciler stopped")

    @property
    def history(self) -> list[ReconciliationResult]:
        return list(self._reconciliation_history)

    def get_stats(self) -> dict[str, Any]:
        """Return reconciliation statistics."""
        total_runs = len(self._reconciliation_history)
        total_updated = sum(r.status_updated for r in self._reconciliation_history)
        total_errors = sum(len(r.errors) for r in self._reconciliation_history)
        return {
            "total_runs": total_runs,
            "total_status_updates": total_updated,
            "total_errors": total_errors,
            "is_running": self._running,
        }
