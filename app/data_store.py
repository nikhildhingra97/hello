"""In-memory data store for the control tower."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Mapping

from .models import (
    ControlTowerSnapshot,
    DemandSignal,
    InventoryItem,
    InventoryStatus,
    ReplenishmentOrder,
)


def _ensure_inventory_item(item: InventoryItem | Mapping[str, object]) -> InventoryItem:
    if isinstance(item, InventoryItem):
        return InventoryItem(**item.to_dict())
    payload = dict(item)
    status = payload.get("status")
    if isinstance(status, str):
        payload["status"] = InventoryStatus(status)
    return InventoryItem(**payload)  # type: ignore[arg-type]


def _ensure_demand_signal(signal: DemandSignal | Mapping[str, object]) -> DemandSignal:
    if isinstance(signal, DemandSignal):
        return DemandSignal(**signal.to_dict())
    return DemandSignal(**signal)  # type: ignore[arg-type]


def _ensure_order(order: ReplenishmentOrder | Mapping[str, object]) -> ReplenishmentOrder:
    if isinstance(order, ReplenishmentOrder):
        return ReplenishmentOrder(**order.to_dict())
    return ReplenishmentOrder(**order)  # type: ignore[arg-type]


class DataStore:
    """Simple in-memory storage for control tower data."""

    def __init__(self) -> None:
        self._inventory: List[InventoryItem] = []
        self._demand: List[DemandSignal] = []
        self._orders: List[ReplenishmentOrder] = []

    # Inventory operations -------------------------------------------------
    def load_inventory(self, items: Iterable[InventoryItem | Mapping[str, object]]) -> None:
        self._inventory = [_ensure_inventory_item(item) for item in items]

    def upsert_inventory_item(self, item: InventoryItem | Mapping[str, object]) -> None:
        new_item = _ensure_inventory_item(item)
        for idx, existing in enumerate(self._inventory):
            if existing.sku == new_item.sku and existing.warehouse == new_item.warehouse:
                self._inventory[idx] = new_item
                return
        self._inventory.append(new_item)

    def list_inventory(self) -> List[InventoryItem]:
        return [InventoryItem(**item.to_dict()) for item in self._inventory]

    # Demand operations ----------------------------------------------------
    def load_demand(self, signals: Iterable[DemandSignal | Mapping[str, object]]) -> None:
        self._demand = [_ensure_demand_signal(signal) for signal in signals]

    def list_demand(self) -> List[DemandSignal]:
        return [DemandSignal(**signal.to_dict()) for signal in self._demand]

    # Order operations -----------------------------------------------------
    def load_orders(self, orders: Iterable[ReplenishmentOrder | Mapping[str, object]]) -> None:
        self._orders = [_ensure_order(order) for order in orders]

    def list_orders(self) -> List[ReplenishmentOrder]:
        return [ReplenishmentOrder(**order.to_dict()) for order in self._orders]

    # Aggregations ---------------------------------------------------------
    def inventory_totals_by_status(self) -> Dict[str, int]:
        totals: Dict[str, int] = defaultdict(int)
        for item in self._inventory:
            totals[item.status.value] += item.quantity
        return dict(totals)

    def shortfalls_by_sku(self) -> Dict[str, int]:
        shortfalls: Dict[str, int] = defaultdict(int)
        for item in self._inventory:
            shortfalls[item.sku] += item.shortfall()
        return {sku: qty for sku, qty in shortfalls.items() if qty > 0}

    def generate_snapshot(self, generated_on: date) -> ControlTowerSnapshot:
        return ControlTowerSnapshot(
            generated_on=generated_on,
            inventory_by_status=self.inventory_totals_by_status(),
            sku_shortfalls=self.shortfalls_by_sku(),
            top_risk_skus=self.top_risk_skus(limit=5),
        )

    def top_risk_skus(self, limit: int = 5) -> List[str]:
        shortfalls = self.shortfalls_by_sku()
        ordered = sorted(shortfalls.items(), key=lambda item: item[1], reverse=True)
        return [sku for sku, _ in ordered[:limit]]

