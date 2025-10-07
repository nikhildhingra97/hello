"""FastAPI application exposing control tower metrics."""
from __future__ import annotations

from datetime import date
from typing import List

from fastapi import Depends, FastAPI

from .services import ControlTowerService
from .sample_data import load_sample_data

app = FastAPI(title="Control Tower API", version="0.1.0")


def get_service() -> ControlTowerService:
    service = ControlTowerService()
    load_sample_data(service)
    return service


@app.get("/snapshot")
def get_snapshot(service: ControlTowerService = Depends(get_service)) -> dict:
    return service.snapshot(date.today()).to_dict()


@app.get("/sku-health")
def get_sku_health(service: ControlTowerService = Depends(get_service)) -> List[dict]:
    return service.sku_health()


@app.get("/inbound")
def get_inbound(service: ControlTowerService = Depends(get_service)) -> List[dict]:
    return service.inbound_visibility()

