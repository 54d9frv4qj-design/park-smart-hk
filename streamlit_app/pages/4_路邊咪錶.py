# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 路邊咪錶
咪錶地圖/列表/預測 + 收費 + 咪錶 vs 停車場對比
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.config import COLORS, HK_DISTRICTS
from src.db.connection import get_engine, init_db
from src.db.queries import get_all_meters_latest, get_overview_stats
from src.visualization.maps import create_realtime_map
from src.visualization.charts import create_meter_vs_carpark_fig
from streamlit_folium import st_folium

st.set_page_config(page_title="路邊咪錶 — 泊得好", page_icon="⏱️", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>⏱️ 路邊咪錶</h1>", unsafe_allow_html=True)
st.caption("全港路邊咪錶實時狀態｜運輸署真實數據｜咪錶 vs 停車場對比")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()

# 側邊欄
with st.sidebar:
    st.header("⚙️ 篩選")
    selected_district = st.selectbox("地區", ["全部"] + [d["name"] for d in HK_DISTRICTS])
    view_mode = st.radio("顯示模式", ["地圖", "列表", "對比"])
    only_vacant = st.checkbox("只顯示有位嘅咪錶")

# 載入數據
meters_df = get_all_meters_latest(engine)
if meters_df.empty:
    st.info("暫無咪錶數據，請先初始化模擬數據")
    st.stop()

if selected_district != "全部":
    meters_df = meters_df[meters_df["district"] == selected_district]
if only_vacant:
    meters_df = meters_df[meters_df["vacant_spaces"].fillna(0) > 0]

# 統計
col1, col2, col3, col4 = st.columns(4)
col1.metric("咪錶組數", len(meters_df))
col2.metric("總車位", int(meters_df["total_spaces"].sum()))
col3.metric("平均時租", f"HK${meters_df['hourly_fee'].mean():.0f}" if not meters_df.empty else "N/A")
col4.metric("有位比率", f"{(meters_df['vacant_spaces'].fillna(0) > 0).mean():.0%}" if not meters_df.empty else "N/A")

st.divider()

if view_mode == "地圖":
    st.subheader("🗺️ 咪錶地圖")

    if selected_district == "全部":
        # ===== 按區聚合顯示（18個標記）=====
        st.caption("💡 點擊側邊欄選擇地區，可查看該區嘅個別咪錶位置")

        # 按區聚合統計
        district_stats = meters_df.groupby("district").agg(
            meter_count=("meter_id", "count"),
            total_spaces=("total_spaces", "sum"),
            vacant_spaces=("vacant_spaces", "sum"),
            avg_lat=("lat", "mean"),
            avg_lng=("lng", "mean"),
            avg_fee=("hourly_fee", "mean"),
        ).reset_index()

        # 計算有位比率同狀態
        district_stats["vacancy_rate"] = district_stats["vacant_spaces"] / district_stats["total_spaces"]
        district_stats["status"] = district_stats["vacancy_rate"].apply(
            lambda x: "green" if x > 0.3 else ("yellow" if x > 0.1 else "red")
        )

        # 生成區級標記
        district_points = []
        for _, row in district_stats.iterrows():
            vacant = int(row["vacant_spaces"]) if row["vacant_spaces"] == int(row["vacant_spaces"]) else row["vacant_spaces"]
            total = int(row["total_spaces"]) if row["total_spaces"] == int(row["total_spaces"]) else row["total_spaces"]
            occ_rate = max(0.0, min(1.0, 1.0 - float(vacant) / float(total))) if total else 0.0
            district_points.append({
                "lat": row["avg_lat"],
                "lng": row["avg_lng"],
                "name": f"{row['district']}（{int(row['meter_count'])}個咪錶）",
                "vacancy": vacant,
                "total_spaces": total,
                "occupancy_rate": occ_rate,
                "status": row["status"],
                "hourly_fee": round(row["avg_fee"], 1),
                "district": row["district"],
            })

        m = create_realtime_map(district_points, zoom=11)
        st_folium(m, width="100%", height=550, returned_objects=[])

        # 顯示各區統計表格
        st.subheader("📊 各區咪錶統計")
        display_df = district_stats[["district", "meter_count", "total_spaces", "vacant_spaces", "vacancy_rate", "avg_fee"]].copy()
        display_df.columns = ["地區", "咪錶組數", "總車位", "空位", "有位比率", "平均時租"]
        display_df["有位比率"] = display_df["有位比率"].apply(lambda x: f"{x:.0%}")
        display_df["平均時租"] = display_df["平均時租"].apply(lambda x: f"HK${x:.0f}")
        display_df = display_df.sort_values("有位比率", ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        # ===== 具體區：顯示個別咪錶 =====
        st.caption(f"📍 {selected_district} — 顯示個別咪錶位置")
        meters_sorted = meters_df.sort_values("vacant_spaces", ascending=False)
        map_limit = min(500, len(meters_sorted))
        meters_for_map = meters_sorted.head(map_limit)
        meter_points = [{
            "lat": m["lat"], "lng": m["lng"],
            "name": m.get("street_name", "咪錶"),
            "vacancy": int(m["vacant_spaces"]) if pd.notna(m["vacant_spaces"]) else 0,
            "total_spaces": int(m["total_spaces"]) if pd.notna(m["total_spaces"]) else 1,
            "status": m.get("status", "unknown"),
            "hourly_fee": m.get("hourly_fee"),
            "district": m.get("district", ""),
        } for _, m in meters_for_map.iterrows()]

        if len(meters_df) > map_limit:
            st.caption(f"💡 地圖顯示 {map_limit} 個咪錶（優先顯示有位），完整列表請切換到「列表」模式")

        m = create_realtime_map(meter_points, zoom=13)
        st_folium(m, width="100%", height=550, returned_objects=[])

elif view_mode == "列表":
    st.subheader("📋 咪錶列表")
    display_df = meters_df[[
        "meter_id", "street_name", "district", "total_spaces",
        "vacant_spaces", "occupancy_rate", "hourly_fee", "max_duration"
    ]].copy()
    display_df.columns = ["編號", "街道", "地區", "總車位", "空位", "佔用率", "時租(HKD)", "最長(分鐘)"]
    display_df["佔用率"] = display_df["佔用率"].apply(lambda x: f"{x:.0%}" if x else "N/A")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:  # 對比
    st.subheader("⚖️ 咪錶 vs 停車場")
    stats = get_overview_stats(engine)
    meter_data = {
        "avg_fee": meters_df["hourly_fee"].mean(),
        "avg_vacancy_rate": 1 - meters_df["occupancy_rate"].mean(),
        "coverage": min(100, len(meters_df) / max(1, len(meters_df)) * 100),
    }
    carpark_data = {
        "avg_fee": 30,  # 模擬
        "avg_vacancy_rate": 1 - (stats.get("avg_occupancy", 0.5) or 0.5),
        "coverage": min(100, stats.get("total_carparks", 607) / 607 * 100),
    }
    fig = create_meter_vs_carpark_fig(meter_data, carpark_data)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    ### 點樣揀？
    - **短時間（<2小時）**：路邊咪錶通常較平，即泊即走
    - **長時間（>2小時）**：停車場日租可能更抵，有蓋唔使曬雨淋
    - **核心商業區**：咪錶位長期滿，建議預約停車場
    - **住宅區**：路邊咪錶夜晚可能免費，留意牌面標示
    """)
