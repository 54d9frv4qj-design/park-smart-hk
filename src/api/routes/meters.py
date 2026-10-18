# -*- coding: utf-8 -*-
"""端點：GET /api/meters — 路邊咪錶列表/地圖數據"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.connection import get_engine
from src.db.queries import get_all_meters_latest
from src.api.schemas import MeterInfo

router = APIRouter()


@router.get("/meters")
async def get_meters(
    district: Optional[str] = Query(None, description="按地區篩選"),
    status: Optional[str] = Query(None, description="按狀態篩選"),
    limit: int = Query(200, description="返回數量"),
):
    """取得路邊咪錶實時狀態"""
    engine = get_engine()
    df = get_all_meters_latest(engine)

    if district:
        df = df[df["district"] == district]
    if status:
        df = df[df["status"] == status]

    df = df.head(limit)

    meters = []
    for _, row in df.iterrows():
        meters.append(MeterInfo(
            meter_id=str(row.get("meter_id", "")),
            street_name=str(row.get("street_name", "")),
            district=str(row.get("district", "")),
            lat=float(row.get("lat", 0)),
            lng=float(row.get("lng", 0)),
            total_spaces=int(row.get("total_spaces", 0)),
            vacant_spaces=int(row["vacant_spaces"]) if row.get("vacant_spaces") is not None else None,
            occupancy_rate=float(row["occupancy_rate"]) if row.get("occupancy_rate") is not None else None,
            status=str(row.get("status", "unknown")),
            hourly_fee=float(row["hourly_fee"]) if row.get("hourly_fee") is not None else None,
            max_duration=int(row.get("max_duration", 120)),
            is_interpolated=int(row.get("is_interpolated", 0)),
        ))

    return {"meters": meters, "count": len(meters)}
