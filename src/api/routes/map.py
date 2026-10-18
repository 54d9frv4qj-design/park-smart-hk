# -*- coding: utf-8 -*-
"""端點：GET /api/map — 地圖數據（所有停車場位置+狀態）"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.connection import get_engine
from src.db.queries import get_all_latest_status
from src.api.schemas import MapResponse, MapPoint

router = APIRouter()


@router.get("/map", response_model=MapResponse)
async def get_map_data(
    district: Optional[str] = Query(None, description="按地區篩選"),
    vehicle_type: str = Query("privateCar", description="車型"),
):
    """取得全港停車場地圖數據"""
    engine = get_engine()
    df = get_all_latest_status(engine)

    if district:
        df = df[df["district"] == district]

    points = []
    for _, row in df.iterrows():
        points.append(MapPoint(
            park_id=str(row.get("park_id", "")),
            name=str(row.get("name", "")),
            district=str(row.get("district", "")),
            lat=float(row.get("lat", 0)),
            lng=float(row.get("lng", 0)),
            vacancy=int(row["vacancy"]) if row.get("vacancy") is not None else None,
            total_spaces=int(row.get("total_spaces", 0)),
            occupancy_rate=float(row["occupancy_rate"]) if row.get("occupancy_rate") is not None else None,
            status=str(row.get("status", "unknown")),
            hourly_fee=float(row["hourly_fee"]) if row.get("hourly_fee") is not None else None,
        ))

    return MapResponse(points=points, count=len(points))
