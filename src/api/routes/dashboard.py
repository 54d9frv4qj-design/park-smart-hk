# -*- coding: utf-8 -*-
"""端點：GET /api/dashboard — 儀表板數據"""
from fastapi import APIRouter, Query
from src.db.connection import get_engine
from src.db.queries import (
    get_overview_stats, get_district_ranking,
    get_7x24_heatmap, get_timeseries_data,
)

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(days: int = Query(14, description="趨勢天數")):
    """取得儀表板數據（統計+排名+熱力圖+趨勢）"""
    engine = get_engine()

    # 總覽
    overview = get_overview_stats(engine)

    # 地區排名
    ranking_df = get_district_ranking(engine)
    ranking = ranking_df.to_dict("records") if not ranking_df.empty else []

    # 7×24 熱力圖
    heatmap_df = get_7x24_heatmap(engine)
    heatmap = {}
    if not heatmap_df.empty:
        heatmap = {
            "weekdays": list(heatmap_df.index),
            "hours": list(heatmap_df.columns),
            "values": heatmap_df.values.tolist(),
        }

    # 14 天趨勢
    trend_df = get_timeseries_data(engine, days=days)
    trend = trend_df.to_dict("records") if not trend_df.empty else []

    return {
        "overview": {k: (float(v) if isinstance(v, float) else v) for k, v in overview.items()},
        "district_ranking": ranking,
        "heatmap_7x24": heatmap,
        "trend_14d": trend,
    }
