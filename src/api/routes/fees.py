# -*- coding: utf-8 -*-
"""端點：GET /api/fees — 收費比較數據"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.connection import get_engine
from src.db.queries import get_fee_comparison

router = APIRouter()


@router.get("/fees")
async def get_fees(
    district: Optional[str] = Query(None, description="按地區篩選"),
    sort_by: str = Query("hourly_fee", description="排序欄位"),
    limit: int = Query(100, description="返回數量"),
):
    """取得停車場收費比較數據"""
    engine = get_engine()
    df = get_fee_comparison(engine, district=district, sort_by=sort_by)
    df = df.head(limit)

    fees = df.to_dict("records")
    # 轉換 NaN
    for r in fees:
        for k, v in r.items():
            if isinstance(v, float) and __import__("math").isnan(v):
                r[k] = None

    return {"fees": fees, "count": len(fees)}
