# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 首頁
搜尋欄 + 統計卡 + Folium 地圖 + 最易泊/最緊張 Top 5
"""
import sys
from pathlib import Path

# 確保項目根目錄在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.config import COLORS, APP_NAME
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_overview_stats, get_all_latest_status,
    get_district_ranking, search_carparks,
)
from src.visualization.maps import create_realtime_map
from src.visualization.charts import create_stats_cards
from streamlit_folium import st_folium

# 頁面配置
st.set_page_config(
    page_title=f"{APP_NAME} — 首頁",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自訂 CSS
st.markdown(f"""
<style>
    .main .block-container {{ padding-top: 2rem; }}
    h1, h2, h3 {{ color: {COLORS['primary']}; }}
    .stat-card {{
        background: linear-gradient(135deg, {COLORS['secondary_bg']}, white);
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid {COLORS['accent']};
        margin-bottom: 1rem;
    }}
    .stat-value {{ font-size: 2rem; font-weight: bold; color: {COLORS['primary']}; }}
    .stat-label {{ font-size: 0.9rem; color: #666; }}
</style>
""", unsafe_allow_html=True)

# 初始化 DB
@st.cache_resource
def get_db_engine():
    engine = get_engine()
    init_db(engine)
    return engine

engine = get_db_engine()

# ============================================================
# 頁面標題
# ============================================================
st.title("🅿️ 泊得好 Park Smart HK")
st.markdown(f"**香港智能停車**｜邊度好泊車？泊得好話你知！")
st.divider()

# ============================================================
# 搜尋欄
# ============================================================
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    search_query = st.text_input("🔍 搜尋停車場（名稱 / 地址 / 地區）", "")
with col2:
    district_filter = st.selectbox("地區", ["全部"] + [d["name"] for d in __import__("src.config", fromlist=["HK_DISTRICTS"]).HK_DISTRICTS])
with col3:
    vehicle_type = st.selectbox("車型", ["私家車", "電動車", "貨車", "電單車"])

if search_query or district_filter != "全部":
    results = search_carparks(
        engine,
        keyword=search_query,
        district=district_filter if district_filter != "全部" else "",
    )
    if not results.empty:
        st.success(f"找到 {len(results)} 個停車場")
        st.dataframe(
            results[["name", "district", "total_spaces", "hourly_fee", "address"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("搵唔到符合條件嘅停車場，試下其他關鍵字？")

# ============================================================
# 統計卡
# ============================================================
st.subheader("📊 全港即時統計")
stats = get_overview_stats(engine)
cards = create_stats_cards(stats)

cols = st.columns(4)
for i, card in enumerate(cards):
    with cols[i]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{card['icon']} {card['label']}</div>
            <div class="stat-value" style="color:{card['color']};">{card['value']}</div>
            <div style="font-size:0.8rem;color:#888;">{card['delta']}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ============================================================
# 地圖 + Top 5
# ============================================================
col_map, col_top = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ 全港停車場分佈")
    all_status = get_all_latest_status(engine)
    if not all_status.empty:
        carparks_list = all_status.to_dict("records")
        m = create_realtime_map(carparks_list, zoom=11)
        st_folium(m, width="100%", height=450, returned_objects=[])
    else:
        st.info("暫無地圖數據，請先初始化資料庫")

with col_top:
    st.subheader("🏆 最易泊 Top 5")
    ranking = get_district_ranking(engine)
    if not ranking.empty:
        easiest = ranking.nsmallest(5, "avg_occupancy")
        for _, row in easiest.iterrows():
            st.markdown(
                f"**{row['district']}**　"
                f"佔用率 {row['avg_occupancy']:.0%}　"
                f"{int(row['carpark_count'])} 個場"
            )

    st.divider()
    st.subheader("😰 最緊張 Top 5")
    if not ranking.empty:
        crowded = ranking.nlargest(5, "avg_occupancy")
        for _, row in crowded.iterrows():
            st.markdown(
                f"**{row['district']}**　"
                f"佔用率 {row['avg_occupancy']:.0%}　"
                f"{int(row['carpark_count'])} 個場"
            )

# ============================================================
# 側邊欄
# ============================================================
with st.sidebar:
    st.markdown(f"### 🅿️ {APP_NAME}")
    st.markdown("---")
    st.markdown("**快速連結**")
    st.page_link("pages/1_實時地圖.py", label="🗺️ 實時地圖")
    st.page_link("pages/2_停車場詳情.py", label="📋 停車場詳情")
    st.page_link("pages/3_AI對話.py", label="💬 AI 對話")
    st.page_link("pages/4_路邊咪錶.py", label="⏱️ 路邊咪錶")
    st.page_link("pages/5_儀表板.py", label="📊 儀表板")
    st.page_link("pages/6_收費比較.py", label="💰 收費比較")
    st.page_link("pages/7_關於.py", label="ℹ️ 關於")
    st.markdown("---")
    st.caption("數據來源：香港政府數據一站通")
    st.caption("更新：每 10 分鐘自動刷新")
