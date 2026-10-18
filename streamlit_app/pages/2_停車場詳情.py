# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 停車場詳情
即時狀態 + 預測 + 24h歷史 + 未來預測 + 7×24熱力圖 + 替代 + AI建議 + 導航
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.config import COLORS
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_all_carparks, get_carpark_by_id, get_latest_vacancy,
    get_vacancy_history, get_nearby_carparks,
)
from src.visualization.maps import create_carpark_detail_map
from src.visualization.heatmaps import create_7x24_heatmap_fig
from src.eda.distributions import get_7x24_heatmap_data
from streamlit_folium import st_folium

st.set_page_config(page_title="停車場詳情 — 泊得好", page_icon="📋", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>📋 停車場詳情</h1>", unsafe_allow_html=True)

@st.cache_resource
def get_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_engine()

# 選擇停車場
carparks = get_all_carparks(engine)
if carparks.empty:
    st.info("暫無停車場數據")
    st.stop()

park_options = [f"{row['park_id']} - {row['name']}（{row['district']}）"
                for _, row in carparks.iterrows()]
selected = st.selectbox("選擇停車場", park_options)
park_id = selected.split(" - ")[0]

# 載入詳情
detail = get_carpark_by_id(engine, park_id)
realtime = get_latest_vacancy(engine, park_id) or {}

if not detail:
    st.error("搵唔到呢個停車場")
    st.stop()

# ============================================================
# 即時狀態大卡片
# ============================================================
vacancy = realtime.get("vacancy", 0)
total = detail.get("total_spaces", 0)
occupancy = realtime.get("occupancy_rate", 0) or 0
status = realtime.get("status", "unknown")
status_colors = {"green": "#2ECC71", "yellow": "#F1C40F", "red": "#E74C3C", "full": "#E74C3C"}
status_labels = {"green": "充足", "yellow": "偏緊", "red": "緊張", "full": "滿座", "unknown": "未知"}

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("即時空位", f"{vacancy} / {total}")
with col2:
    st.metric("佔用率", f"{occupancy:.1%}")
with col3:
    st.markdown(f"<div style='text-align:center;padding:10px;background:{status_colors.get(status,'#999')};color:white;border-radius:8px;font-size:1.2rem;font-weight:bold;'>{status_labels.get(status,'未知')}</div>", unsafe_allow_html=True)
with col4:
    st.metric("時租", f"HK${detail.get('hourly_fee', 'N/A')}")

# 進度條
st.progress(occupancy)
st.caption(f"更新時間：{realtime.get('snapshot_time', 'N/A')}")

st.divider()

# ============================================================
# 預測 + 歷史圖
# ============================================================
col_pred, col_hist = st.columns(2)

with col_pred:
    st.subheader("🔮 未來預測")
    pred_30 = max(0, int(vacancy) - 2) if vacancy else 0
    pred_60 = max(0, int(vacancy) - 4) if vacancy else 0
    c1, c2 = st.columns(2)
    c1.metric("30 分鐘後", f"{pred_30} 位", delta=f"{pred_30 - vacancy}")
    c2.metric("60 分鐘後", f"{pred_60} 位", delta=f"{pred_60 - vacancy}")

    # 預測走勢圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=["而家", "15min", "30min", "45min", "60min"],
        y=[vacancy, max(0, vacancy-1), pred_30, max(0, pred_30-1), pred_60],
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=3),
        fill="tozeroy",
    ))
    fig.update_layout(title="空位預測走勢", height=250, margin=dict(l=40,r=20,t=40,b=30))
    st.plotly_chart(fig, use_container_width=True)

with col_hist:
    st.subheader("📈 24 小時歷史")
    history = get_vacancy_history(engine, park_id, hours=24)
    if not history.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(history["snapshot_time"]),
            y=history["vacancy"],
            mode="lines",
            line=dict(color=COLORS["primary"], width=2),
            fill="tozeroy",
        ))
        fig.update_layout(title="過去 24 小時空位", height=250, margin=dict(l=40,r=20,t=40,b=30))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無歷史數據")

st.divider()

# ============================================================
# 7×24 熱力圖 + 地圖
# ============================================================
col_heat, col_map = st.columns(2)

with col_heat:
    st.subheader("🔥 7×24 繁忙熱力圖")
    heatmap = get_7x24_heatmap_data(engine)
    if not heatmap.empty:
        fig = create_7x24_heatmap_fig(heatmap, title=f"{detail['name']} 繁忙模式")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無熱力圖數據")

with col_map:
    st.subheader("📍 位置地圖")
    alternatives = get_nearby_carparks(engine, detail["lat"], detail["lng"], radius_km=1, limit=5)
    alt_list = alternatives.to_dict("records") if not alternatives.empty else []
    m = create_carpark_detail_map(detail, alternatives=alt_list)
    st_folium(m, width="100%", height=350, returned_objects=[])

st.divider()

# ============================================================
# 替代停車場
# ============================================================
st.subheader("🔄 附近替代停車場")
if not alternatives.empty:
    for _, row in alternatives.iterrows():
        if str(row.get("park_id")) == park_id:
            continue
        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
        with col_a:
            st.markdown(f"**{row.get('name', '')}**　{row.get('district', '')}")
        with col_b:
            st.metric("空位", row.get("vacancy", "?"))
        with col_c:
            st.metric("距離", f"{row.get('distance_km', '?')}km")
        with col_d:
            st.metric("時租", f"HK${row.get('hourly_fee', '?')}")

st.divider()

# ============================================================
# AI 建議 + 導航
# ============================================================
st.subheader("💡 AI 泊車建議")
if status == "green":
    st.success(f"而家 **{detail['name']}** 空位充足（{vacancy}/{total}），建議你直接去！30 分鐘後預測仲有 {pred_30} 個位。")
elif status == "yellow":
    st.warning(f"而家 **{detail['name']}** 偏緊（{vacancy}/{total}），60 分鐘後可能更緊張。如果可以，建議考慮附近替代停車場。")
else:
    st.error(f"而家 **{detail['name']}** 好緊張（{vacancy}/{total}），建議你揀上面嘅替代停車場，避免白行一趟。")

# 導航按鈕
st.subheader("🧭 導航")
col_g, col_w = st.columns(2)
with col_g:
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={detail['lat']},{detail['lng']}"
    st.link_button("🗺️ Google Maps 導航", maps_url, use_container_width=True)
with col_w:
    waze_url = f"https://www.waze.com/ul?ll={detail['lat']},{detail['lng']}&navigate=yes"
    st.link_button("🚗 Waze 導航", waze_url, use_container_width=True)
