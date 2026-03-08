from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    symbol: str
    quantity: float


@dataclass(frozen=True)
class FillRecord:
    order_id: str
    filled_qty: float


@dataclass(frozen=True)
class ReconciliationResult:
    matched: int
    missing_fills: list[str]
    qty_mismatches: list[str]


class FillReconciliationMonitor:
    def reconcile(self, orders: list[OrderRecord], fills: list[FillRecord]) -> ReconciliationResult:
        fill_map = {f.order_id: f for f in fills}
        missing: list[str] = []
        mismatched: list[str] = []
        matched = 0

        for order in orders:
            fill = fill_map.get(order.order_id)
            if fill is None:
                missing.append(order.order_id)
                continue
            if abs(fill.filled_qty - order.quantity) > 1e-9:
                mismatched.append(order.order_id)
                continue
            matched += 1

        return ReconciliationResult(matched=matched, missing_fills=missing, qty_mismatches=mismatched)
