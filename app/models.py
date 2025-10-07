"""Domain models for the supply chain control tower."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional


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

