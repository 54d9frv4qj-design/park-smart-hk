# -*- coding: utf-8 -*-
"""端點：GET /api/detail/{park_id} — 停車場詳情"""
from fastapi import APIRouter, HTTPException
from src.db.connection import get_engine
from src.db.queries import get_carpark_by_id, get_latest_vacancy
from src.api.schemas import CarparkDetail

router = APIRouter()


@router.get("/detail/{park_id}", response_model=CarparkDetail)
async def get_carpark_detail(park_id: str):
    """取得單個停車場詳情（含實時狀態與預測）"""
    engine = get_engine()
    static = get_carpark_by_id(engine, park_id)
    if not static:
        raise HTTPException(status_code=404, detail=f"停車場 {park_id} 唔存在")

    realtime = get_latest_vacancy(engine, park_id) or {}

    # 簡單預測：基於最近趨勢（實際部署用訓練好的模型）
    vacancy = realtime.get("vacancy")
    pred_30 = None
    pred_60 = None
    if vacancy is not None:
        # 模擬預測：基於時間段的簡單調整
        from src.utils.haversine import now_hkt
        hour = now_hkt().hour
        adjustment = -2 if 7 <= hour < 9 or 17 <= hour < 19 else 2
        pred_30 = max(0, int(vacancy) + adjustment)
        pred_60 = max(0, int(vacancy) + adjustment * 2)

    return CarparkDetail(
        park_id=static["park_id"],
        name=static.get("name", ""),
        name_en=static.get("name_en"),
        district=static.get("district", ""),
        address=static.get("address"),
        lat=float(static.get("lat", 0)),
        lng=float(static.get("lng", 0)),
        total_spaces=int(static.get("total_spaces", 0)),
        ev_spaces=int(static.get("ev_spaces", 0)),
        vacancy=int(realtime["vacancy"]) if realtime.get("vacancy") is not None else None,
        occupancy_rate=float(realtime["occupancy_rate"]) if realtime.get("occupancy_rate") is not None else None,
        status=str(realtime.get("status", "unknown")),
        hourly_fee=float(static["hourly_fee"]) if static.get("hourly_fee") is not None else None,
        daily_fee=float(static["daily_fee"]) if static.get("daily_fee") is not None else None,
        monthly_fee=float(static["monthly_fee"]) if static.get("monthly_fee") is not None else None,
        is_government=int(static.get("is_government", 0)),
        has_ev_charging=int(static.get("has_ev_charging", 0)),
        prediction_30min=pred_30,
        prediction_60min=pred_60,
        update_time=str(realtime.get("snapshot_time", "")),
    )
