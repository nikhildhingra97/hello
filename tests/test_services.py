"""Unit tests for the control tower service."""
from __future__ import annotations

from datetime import date, timedelta

from app.models import DemandSignal, InventoryItem, InventoryStatus, ReplenishmentOrder
from app.services import ControlTowerService


def build_service() -> ControlTowerService:
    service = ControlTowerService()
    service.load_inventory(
        [
            InventoryItem("SKU-1", "WH-A", 100, InventoryStatus.ON_HAND, safety_stock=120),
            InventoryItem("SKU-2", "WH-A", 30, InventoryStatus.ON_HAND, safety_stock=20),
            InventoryItem("SKU-3", "WH-B", 0, InventoryStatus.BACKORDER, safety_stock=40),
        ]
    )
    service.load_demand(
        [
            DemandSignal("SKU-1", date.today(), date.today() + timedelta(days=30), 600),
            DemandSignal("SKU-2", date.today(), date.today() + timedelta(days=30), 60),
        ]
    )
    service.load_orders(
        [
            ReplenishmentOrder("PO-1", "SKU-1", "SUP-1", "WH-A", date.today() + timedelta(days=2), 150),
        ReplenishmentOrder("PO-2", "SKU-3", "SUP-2", "WH-B", date.today() + timedelta(days=5), 20),
        ]
    )
    return service


def test_snapshot_shortfalls_and_risks() -> None:
    service = build_service()
    snapshot = service.snapshot(date.today())

    assert snapshot.inventory_by_status[InventoryStatus.ON_HAND] == 130
    assert snapshot.inventory_by_status[InventoryStatus.BACKORDER] == 0
    assert snapshot.sku_shortfalls["SKU-1"] == 20
    assert "SKU-1" in snapshot.top_risk_skus
    assert "SKU-3" in snapshot.top_risk_skus


def test_sku_health_includes_coverage_days() -> None:
    service = build_service()
    health = {row["sku"]: row for row in service.sku_health()}

    assert health["SKU-1"]["shortfall"] == 20
    assert health["SKU-1"]["coverage_days"] == 5  # 100 qty / (600/30)
    assert health["SKU-2"]["coverage_days"] == 15  # 30 qty / (60/30)


def test_inbound_visibility_includes_shortfall_context() -> None:
    service = build_service()
    inbound = {row["order_id"]: row for row in service.inbound_visibility()}

    assert inbound["PO-1"]["covers_shortfall"] is True
    assert inbound["PO-2"]["covers_shortfall"] is False

