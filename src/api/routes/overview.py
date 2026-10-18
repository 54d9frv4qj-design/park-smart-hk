# -*- coding: utf-8 -*-
"""端點：GET /api/overview — 全港統計總覽"""
from fastapi import APIRouter
from src.db.connection import get_engine
from src.db.queries import get_overview_stats
from src.api.schemas import OverviewResponse

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
async def get_overview():
    """取得全港停車場統計總覽"""
    engine = get_engine()
    stats = get_overview_stats(engine)

    # 咪錶數量
    from sqlalchemy import text
    with engine.connect() as conn:
        meter_count = conn.execute(
            text("SELECT COUNT(*) FROM metered_parking")
        ).scalar()

    return OverviewResponse(
        total_carparks=int(stats.get("total_carparks", 0)),
        total_spaces=int(stats.get("total_spaces", 0)),
        avg_occupancy=float(stats.get("avg_occupancy", 0) or 0),
        green_count=int(stats.get("green_count", 0)),
        yellow_count=int(stats.get("yellow_count", 0)),
        red_count=int(stats.get("red_count", 0)),
        total_meters=int(meter_count or 0),
        update_time=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
