"""Single-file control tower prototype for Colab or standalone execution."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional

from fastapi import FastAPI


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class InventoryStatus(str, Enum):
    """Status categories for inventory positions."""

    ON_HAND = "on_hand"
    IN_TRANSIT = "in_transit"
    RESERVED = "reserved"
    BACKORDER = "backorder"


@dataclass
class InventoryItem:
    """Represents a single SKU at a given warehouse."""

    sku: str
    warehouse: str
    quantity: int
    status: InventoryStatus = InventoryStatus.ON_HAND
    safety_stock: int = 0
    demand_forecast: Optional[int] = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")
        if self.safety_stock < 0:
            raise ValueError("safety_stock cannot be negative")
        if self.demand_forecast is not None and self.demand_forecast < 0:
            raise ValueError("demand_forecast cannot be negative")

    def shortfall(self) -> int:
        """Return the shortfall against safety stock, if any."""

        deficit = self.safety_stock - self.quantity
        return max(deficit, 0)

    def coverage_days(self, average_daily_demand: float) -> Optional[float]:
        """Estimate coverage in days based on average demand."""

        if average_daily_demand <= 0:
            return None
        return round(self.quantity / average_daily_demand, 2)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class DemandSignal:
    """Represents forecast demand for a SKU."""

    sku: str
    period_start: date
    period_end: date
    forecast_qty: int

    def __post_init__(self) -> None:
        if self.forecast_qty < 0:
            raise ValueError("forecast_qty cannot be negative")

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ReplenishmentOrder:
    """Represents inbound supply."""

    order_id: str
    sku: str
    origin: str
    destination: str
    expected_arrival: date
    quantity: int
    status: str = "planned"

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ControlTowerSnapshot:
    """Aggregated metrics for a control tower dashboard."""

    generated_on: date
    inventory_by_status: Dict[str, int]
    sku_shortfalls: Dict[str, int]
    top_risk_skus: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "generated_on": self.generated_on.isoformat(),
            "inventory_by_status": self.inventory_by_status,
            "sku_shortfalls": self.sku_shortfalls,
            "top_risk_skus": self.top_risk_skus,
        }


# ---------------------------------------------------------------------------
# In-memory data store
# ---------------------------------------------------------------------------


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
        totals: Dict[str, int] = {status.value: 0 for status in InventoryStatus}
        for item in self._inventory:
            totals[item.status.value] += item.quantity
        return totals

    def shortfalls_by_sku(self) -> Dict[str, int]:
        shortfalls: Dict[str, int] = {}
        for item in self._inventory:
            delta = item.shortfall()
            if delta > 0:
                shortfalls[item.sku] = shortfalls.get(item.sku, 0) + delta
        return shortfalls

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


# ---------------------------------------------------------------------------
# Business services
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Sample data loader
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    service = ControlTowerService()
    load_sample_data(service)

    app = FastAPI(title="Control Tower API", version="0.2.0")

    @app.get("/snapshot")
    def get_snapshot() -> dict:
        return service.snapshot(date.today()).to_dict()

    @app.get("/sku-health")
    def get_sku_health() -> List[dict]:
        return service.sku_health()

    @app.get("/inbound")
    def get_inbound() -> List[dict]:
        return service.inbound_visibility()

    return app


app = create_app()


# ---------------------------------------------------------------------------
# CLI helpers for Colab usage
# ---------------------------------------------------------------------------


def _print_demo_outputs(service: ControlTowerService) -> None:
    print("\n=== Control Tower Snapshot ===")
    print(json.dumps(service.snapshot().to_dict(), indent=2))

    print("\n=== SKU Health ===")
    print(json.dumps(service.sku_health(), indent=2))

    print("\n=== Inbound Visibility ===")
    print(json.dumps(service.inbound_visibility(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Supply chain control tower prototype")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start a FastAPI server instead of printing demo analytics",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind when serving the API"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind when serving the API"
    )
    args = parser.parse_args()

    service = ControlTowerService()
    load_sample_data(service)

    if args.serve:
        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port, reload=False)
    else:
        _print_demo_outputs(service)


if __name__ == "__main__":
    main()
