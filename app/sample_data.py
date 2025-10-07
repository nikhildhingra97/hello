"""Utilities for loading sample control tower data."""
from __future__ import annotations

from datetime import date, timedelta

from .models import DemandSignal, InventoryItem, InventoryStatus, ReplenishmentOrder
from .services import ControlTowerService


def load_sample_data(service: ControlTowerService) -> None:
    today = date.today()
    service.load_inventory(
        [
            InventoryItem("SKU-100", "WH-ATL", 120, InventoryStatus.ON_HAND, safety_stock=100, demand_forecast=300),
            InventoryItem("SKU-100", "WH-LAX", 50, InventoryStatus.ON_HAND, safety_stock=120, demand_forecast=300),
            InventoryItem("SKU-200", "WH-ATL", 80, InventoryStatus.ON_HAND, safety_stock=150, demand_forecast=500),
            InventoryItem("SKU-300", "WH-ORD", 40, InventoryStatus.RESERVED, safety_stock=60, demand_forecast=200),
            InventoryItem("SKU-400", "WH-DFW", 0, InventoryStatus.BACKORDER, safety_stock=80, demand_forecast=150),
            InventoryItem("SKU-500", "WH-DFW", 200, InventoryStatus.IN_TRANSIT, safety_stock=180, demand_forecast=360),
        ]
    )

    service.load_demand(
        [
            DemandSignal("SKU-100", today, today + timedelta(days=30), 600),
            DemandSignal("SKU-200", today, today + timedelta(days=30), 450),
            DemandSignal("SKU-300", today, today + timedelta(days=30), 210),
            DemandSignal("SKU-400", today, today + timedelta(days=30), 120),
        ]
    )

    service.load_orders(
        [
            ReplenishmentOrder("PO-9001", "SKU-100", "SUP-EAST", "WH-LAX", today + timedelta(days=3), 90, status="in_transit"),
            ReplenishmentOrder("PO-9002", "SKU-200", "SUP-WEST", "WH-ATL", today + timedelta(days=5), 150, status="released"),
            ReplenishmentOrder("PO-9003", "SKU-400", "SUP-SOUTH", "WH-DFW", today + timedelta(days=2), 100, status="planned"),
        ]
    )

