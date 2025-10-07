"""Business logic for analytics and alerts."""
from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List, Mapping, Optional

from .data_store import DataStore
from .models import ControlTowerSnapshot, DemandSignal, InventoryItem, ReplenishmentOrder


class ControlTowerService:
    """High-level operations exposed by the control tower."""

    def __init__(self, store: Optional[DataStore] = None) -> None:
        self._store = store or DataStore()

    # Loaders ---------------------------------------------------------------
    def load_inventory(self, items: Iterable[InventoryItem | Mapping[str, object]]) -> None:
        self._store.load_inventory(items)

    def load_demand(self, demand: Iterable[DemandSignal | Mapping[str, object]]) -> None:
        self._store.load_demand(demand)

    def load_orders(self, orders: Iterable[ReplenishmentOrder | Mapping[str, object]]) -> None:
        self._store.load_orders(orders)

    # Queries ---------------------------------------------------------------
    def snapshot(self, generated_on: Optional[date] = None) -> ControlTowerSnapshot:
        generated_on = generated_on or date.today()
        return self._store.generate_snapshot(generated_on)

    def sku_health(self) -> List[Dict[str, object]]:
        """Return a list of SKU health metrics for dashboards."""

        demand_index: Dict[str, int] = {
            signal.sku: signal.forecast_qty for signal in self._store.list_demand()
        }
        health_rows: List[Dict[str, object]] = []
        for item in self._store.list_inventory():
            average_daily_demand = demand_index.get(item.sku, 0) / 30 if item.sku in demand_index else 0
            health_rows.append(
                {
                    "sku": item.sku,
                    "warehouse": item.warehouse,
                    "status": item.status.value,
                    "quantity": item.quantity,
                    "safety_stock": item.safety_stock,
                    "shortfall": item.shortfall(),
                    "coverage_days": item.coverage_days(average_daily_demand),
                }
            )
        return health_rows

    def inbound_visibility(self) -> List[Dict[str, object]]:
        """Return inbound orders joined with shortfall context."""

        shortfalls = self._store.shortfalls_by_sku()
        rows: List[Dict[str, object]] = []
        for order in self._store.list_orders():
            rows.append(
                {
                    "order_id": order.order_id,
                    "sku": order.sku,
                    "expected_arrival": order.expected_arrival.isoformat(),
                    "quantity": order.quantity,
                    "destination": order.destination,
                    "covers_shortfall": shortfalls.get(order.sku, 0) <= order.quantity,
                }
            )
        return rows

