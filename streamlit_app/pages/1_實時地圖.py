# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 實時地圖
全港 607 停車場 CircleMarker，綠/黃/紅狀態色，Popup 含 30/60 分鐘預測
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.config import COLORS, HK_DISTRICTS
from src.db.connection import get_engine, init_db
from src.db.queries import get_all_latest_status, get_all_meters_latest
from src.visualization.maps import create_realtime_map, create_heatmap
from streamlit_folium import st_folium

st.set_page_config(page_title="實時地圖 — 泊得好", page_icon="🗺️", layout="wide")

st.markdown(f"<h1 style='color:{COLORS['primary']}'>🗺️ 全港實時地圖</h1>", unsafe_allow_html=True)
st.caption("點擊停車場標記查看詳情｜綠=充足 黃=偏緊 紅=滿座")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()

# 側邊欄篩選
with st.sidebar:
    st.header("⚙️ 篩選")
    selected_district = st.selectbox("地區", ["全部"] + [d["name"] for d in HK_DISTRICTS])
    status_filter = st.multiselect("狀態", ["green", "yellow", "red", "full"], default=["green", "yellow", "red", "full"])
    show_meters = st.checkbox("顯示路邊咪錶", value=False)
    map_type = st.radio("地圖類型", ["標記地圖", "熱力圖"])
    fee_range = st.slider("時租範圍（HKD）", 0, 100, (0, 100))
    st.divider()
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

# 載入數據
all_status = get_all_latest_status(engine)
if not all_status.empty:
    # 應用篩選
    df = all_status.copy()
    if selected_district != "全部":
        df = df[df["district"] == selected_district]
    if status_filter:
        df = df[df["status"].isin(status_filter)]
    df = df[(df["hourly_fee"].fillna(0) >= fee_range[0]) & (df["hourly_fee"].fillna(0) <= fee_range[1])]

    st.metric("顯示停車場數量", len(df))

    carparks_list = df.to_dict("records")

    # 添加預測到 popup
    for cp in carparks_list:
        if cp.get("vacancy") is not None:
            v = int(cp["vacancy"])
            cp["prediction_30min"] = max(0, v - 2)
            cp["prediction_60min"] = max(0, v - 4)

    meters_list = []
    if show_meters:
        meters_df = get_all_meters_latest(engine)
        if not meters_df.empty:
            if selected_district != "全部":
                meters_df = meters_df[meters_df["district"] == selected_district]
            meters_list = meters_df.to_dict("records")

    if map_type == "標記地圖":
        m = create_realtime_map(carparks_list, show_meters=show_meters, meters=meters_list)
    else:
        m = create_heatmap(carparks_list)

    st_folium(m, width="100%", height=600, returned_objects=[])

    # 狀態統計
    col1, col2, col3, col4 = st.columns(4)
    green = len(df[df["status"] == "green"])
    yellow = len(df[df["status"] == "yellow"])
    red = len(df[df["status"].isin(["red", "full"])])
    with col1:
        st.metric("🟢 充足", green)
    with col2:
        st.metric("🟡 偏緊", yellow)
    with col3:
        st.metric("🔴 滿座", red)
    with col4:
        st.metric("平均空位", f"{df['vacancy'].mean():.0f}" if not df.empty else "N/A")
else:
    st.info("暫無數據，請先執行 `python scripts/init_db.py --mock` 初始化模擬數據")
