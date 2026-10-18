# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 儀表板
全港統計 + 地區排名 + 7×24熱力圖 + 14天趨勢 + 模型表現
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.config import COLORS
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_overview_stats, get_district_ranking,
    get_timeseries_data, get_model_evaluations,
)
from src.visualization.heatmaps import (
    create_7x24_heatmap_fig, create_district_ranking_fig,
    create_trend_fig, create_model_performance_fig,
)
from src.eda.distributions import get_7x24_heatmap_data

st.set_page_config(page_title="儀表板 — 泊得好", page_icon="📊", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>📊 數據儀表板</h1>", unsafe_allow_html=True)

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()

# ============================================================
# 全港統計
# ============================================================
st.subheader("📈 全港統計")
stats = get_overview_stats(engine)
col1, col2, col3, col4 = st.columns(4)
col1.metric("停車場總數", f"{stats.get('total_carparks', 0):,}")
col2.metric("總車位", f"{int(stats.get('total_spaces', 0)):,}")
col3.metric("平均佔用率", f"{stats.get('avg_occupancy', 0):.1%}")
col4.metric("充足/偏緊/滿座", f"{stats.get('green_count',0)}/{stats.get('yellow_count',0)}/{stats.get('red_count',0)}")

st.divider()

# ============================================================
# 地區排名
# ============================================================
st.subheader("🏆 18 區排名（由易泊到緊張）")
ranking = get_district_ranking(engine)
if not ranking.empty:
    fig = create_district_ranking_fig(ranking, value_col="avg_occupancy", ascending=True)
    st.plotly_chart(fig, use_container_width=True)

    # 表格
    display = ranking[["district", "carpark_count", "total_spaces", "avg_occupancy", "avg_vacancy"]].copy()
    display.columns = ["地區", "停車場數", "總車位", "平均佔用率", "平均空位"]
    display["平均佔用率"] = display["平均佔用率"].apply(lambda x: f"{x:.1%}")
    st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# 7×24 熱力圖
# ============================================================
st.subheader("🔥 7×24 時段熱力圖")
heatmap = get_7x24_heatmap_data(engine)
if not heatmap.empty:
    fig = create_7x24_heatmap_fig(heatmap)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暫無熱力圖數據")

st.divider()

# ============================================================
# 14 天趨勢
# ============================================================
st.subheader("📉 14 天趨勢")
trend = get_timeseries_data(engine, days=14)
if not trend.empty:
    trend["datetime"] = pd.to_datetime(trend["date"] + " " + trend["hour"].astype(str) + ":00")
    fig = create_trend_fig(trend, x_col="datetime", y_col="avg_occupancy", title="全港平均佔用率趨勢")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("暫無趨勢數據")

st.divider()

# ============================================================
# 模型表現
# ============================================================
st.subheader("🤖 模型表現")
try:
    evals = get_model_evaluations(engine)
    if not evals.empty:
        st.dataframe(evals, use_container_width=True, hide_index=True)
    else:
        st.info("暫無模型評估數據，執行 `python -m src.models.train_all` 訓練模型")
except Exception:
    st.info("模型評估表尚未建立")

# 模擬模型表現
mock_results = {
    "LightGBM-30min": {"MAE": 3.2, "RMSE": 4.8},
    "LightGBM-60min": {"MAE": 4.5, "RMSE": 6.2},
    "XGBoost-30min": {"MAE": 3.5, "RMSE": 5.1},
    "Prophet": {"MAE": 4.1, "RMSE": 5.8},
}
fig = create_model_performance_fig(mock_results)
st.plotly_chart(fig, use_container_width=True)
