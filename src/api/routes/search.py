# -*- coding: utf-8 -*-
"""端點：GET /api/search — 搜尋停車場/咪錶"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.connection import get_engine
from src.db.queries import search_carparks

router = APIRouter()


@router.get("/search")
async def search(
    q: str = Query("", description="搜尋關鍵字（名稱/地址）"),
    district: Optional[str] = Query(None, description="地區"),
    vehicle_type: str = Query("privateCar", description="車型"),
    limit: int = Query(50, description="返回數量"),
):
    """搜尋停車場"""
    engine = get_engine()
    df = search_carparks(engine, keyword=q, district=district, vehicle_type=vehicle_type)
    df = df.head(limit)

    results = df.to_dict("records")
    # 轉換 NaN 為 None
    for r in results:
        for k, v in r.items():
            if isinstance(v, float) and __import__("math").isnan(v):
                r[k] = None

    return {"query": q, "results": results, "count": len(results)}
