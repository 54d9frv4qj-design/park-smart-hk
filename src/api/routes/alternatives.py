# -*- coding: utf-8 -*-
"""端點：GET /api/alternatives/{park_id} — 替代停車場推薦"""
from fastapi import APIRouter, HTTPException, Query
from src.db.connection import get_engine
from src.db.queries import get_carpark_by_id, get_nearby_carparks
from src.api.schemas import AlternativesResponse, AlternativeCarpark
from src.utils.haversine import haversine_km, walking_minutes

router = APIRouter()


@router.get("/alternatives/{park_id}", response_model=AlternativesResponse)
async def get_alternatives(
    park_id: str,
    radius_km: float = Query(1.0, description="搜尋半徑（公里）"),
    limit: int = Query(5, description="返回數量"),
):
    """取得目標停車場附近的替代停車場"""
    engine = get_engine()
    target = get_carpark_by_id(engine, park_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"停車場 {park_id} 唔存在")

    nearby = get_nearby_carparks(
        engine,
        lat=float(target["lat"]),
        lng=float(target["lng"]),
        radius_km=radius_km,
        limit=limit + 1,  # +1 因為可能包含自己
    )

    alternatives = []
    for _, row in nearby.iterrows():
        if str(row.get("park_id")) == park_id:
            continue
        dist = float(row.get("distance_km", haversine_km(
            target["lat"], target["lng"], row["lat"], row["lng"]
        )))
        alternatives.append(AlternativeCarpark(
            park_id=str(row["park_id"]),
            name=str(row.get("name", "")),
            distance_km=round(dist, 2),
            walking_minutes=walking_minutes(dist * 1000),
            vacancy=int(row["vacancy"]) if row.get("vacancy") is not None else None,
            occupancy_rate=float(row["occupancy_rate"]) if row.get("occupancy_rate") is not None else None,
            status=str(row.get("status", "unknown")),
            hourly_fee=float(row["hourly_fee"]) if row.get("hourly_fee") is not None else None,
        ))
        if len(alternatives) >= limit:
            break

    return AlternativesResponse(
        target_park_id=park_id,
        alternatives=alternatives,
    )
