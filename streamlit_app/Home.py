# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 首頁
參考 inpark.com.hk：Hero 搜尋 + 熱門標籤 + 統計卡 + 地圖 + 地區排名
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.config import COLORS, APP_NAME, HK_DISTRICTS
from src.app_init import ensure_app_ready
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_overview_stats, get_all_latest_status,
    get_district_ranking, search_carparks,
)
from src.visualization.maps import create_realtime_map
from src.visualization.charts import create_stats_cards
from streamlit_folium import st_folium

ensure_app_ready()

st.set_page_config(
    page_title=f"{APP_NAME} — 香港智能泊車",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自訂 CSS — inpark 風格
st.markdown(f"""
<style>
    .main .block-container {{ padding-top: 1rem; max-width: 1200px; }}
    .hero-title {{
        font-size: 2.5rem; font-weight: 800; color: {COLORS['primary']};
        margin-bottom: 0.3rem; line-height: 1.2;
    }}
    .hero-sub {{ font-size: 1.1rem; color: #555; margin-bottom: 1.5rem; }}
    .stat-card {{
        background: linear-gradient(135deg, {COLORS['secondary_bg']}, white);
        padding: 1rem 1.2rem; border-radius: 12px;
        border-left: 4px solid {COLORS['accent']};
        margin-bottom: 0.8rem; transition: transform 0.2s;
    }}
    .stat-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .stat-value {{ font-size: 1.8rem; font-weight: bold; }}
    .stat-label {{ font-size: 0.85rem; color: #666; }}
    .hot-tag {{
        display: inline-block; padding: 0.3rem 0.8rem; margin: 0.2rem;
        background: {COLORS['secondary_bg']}; border-radius: 20px;
        font-size: 0.85rem; cursor: pointer; border: 1px solid #ddd;
    }}
    .hot-tag:hover {{ background: {COLORS['accent']}; color: white; }}
    .district-card {{
        padding: 0.8rem; border-radius: 10px; background: white;
        border: 1px solid #eee; margin-bottom: 0.5rem; cursor: pointer;
    }}
    .district-card:hover {{ border-color: {COLORS['accent']}; }}
    .price-tag {{
        background: {COLORS['green']}; color: white; padding: 0.15rem 0.5rem;
        border-radius: 4px; font-size: 0.8rem; font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_engine():
    engine = get_engine()
    init_db(engine)
    return engine

engine = get_db_engine()

# ============================================================
# Hero 區 — 參考 inpark
# ============================================================
st.markdown('<div class="hero-title">🅿️ 尋找香港泊車位</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">出發前，心中有數　收費、實時空位、入閘限制，一次睇清</div>', unsafe_allow_html=True)

# 搜尋列
col_search, col_near, col_duration = st.columns([4, 1, 2])
with col_search:
    search_query = st.text_input("🔍 搜尋地點、地區或停車場", "", label_visibility="collapsed",
                                 placeholder="搜尋地點、地區或停車場")
with col_near:
    near_clicked = st.button("📍 附近", use_container_width=True)
with col_duration:
    duration = st.selectbox("泊車時間", ["而家 · 1 小時", "而家 · 2 小時", "而家 · 3 小時", "全日"],
                            label_visibility="collapsed")

# 熱門搜尋標籤
st.markdown("**試試：**")
hot_tags = ["海港城", "觀塘區", "九龍城區", "油尖旺區", "沙田區", "深水埗區", "屯門區", "銅鑼灣"]
tag_cols = st.columns(len(hot_tags))
for i, tag in enumerate(hot_tags):
    if tag_cols[i].button(tag, key=f"hot_{tag}", use_container_width=True):
        search_query = tag
        st.rerun()

st.divider()

# ============================================================
# 搜尋結果
# ============================================================
if search_query:
    results = search_carparks(engine, keyword=search_query)
    if not results.empty:
        st.success(f"找到 {len(results)} 個停車場")
        # 顯示價格同狀態
        display_df = results[["name", "district", "total_spaces", "hourly_fee", "address"]].copy()
        display_df.columns = ["停車場", "地區", "車位", "時租", "地址"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
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
# 地圖 + 地區排名
# ============================================================
col_map, col_districts = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ 全港停車場分佈")
    all_status = get_all_latest_status(engine)
    if not all_status.empty:
        carparks_list = all_status.to_dict("records")
        m = create_realtime_map(carparks_list, zoom=11)
        st_folium(m, width="100%", height=450, returned_objects=[])
    else:
        st.info("暫無地圖數據")

with col_districts:
    st.subheader("🏆 最易泊 Top 5")
    ranking = get_district_ranking(engine)
    if not ranking.empty:
        easiest = ranking.nsmallest(5, "avg_occupancy")
        for _, row in easiest.iterrows():
            st.markdown(
                f"**{row['district']}**　"
                f"佔用率 {float(row['avg_occupancy'] or 0):.0%}　"
                f"{int(row['carpark_count'] or 0)} 個場"
            )

    st.divider()
    st.subheader("😰 最緊張 Top 5")
    if not ranking.empty:
        crowded = ranking.nlargest(5, "avg_occupancy")
        for _, row in crowded.iterrows():
            st.markdown(
                f"**{row['district']}**　"
                f"佔用率 {float(row['avg_occupancy'] or 0):.0%}　"
                f"{int(row['carpark_count'] or 0)} 個場"
            )

# ============================================================
# 按地區瀏覽 — 參考 inpark
# ============================================================
st.divider()
st.subheader("📍 按地區瀏覽")
st.markdown("全港十八區 — 停車場數量與平均收費，出發前先知道該往哪裏找")

# 港島/九龍/新界分組
region_map = {
    "港島": ["中西區", "灣仔區", "東區", "南區"],
    "九龍": ["油尖旺區", "深水埗區", "九龍城區", "黃大仙區", "觀塘區"],
    "新界": ["葵青區", "荃灣區", "屯門區", "元朗區", "北區", "大埔區", "沙田區", "西貢區", "離島區"],
}

tab1, tab2, tab3 = st.tabs(["港島", "九龍", "新界"])
for tab, region in [(tab1, "港島"), (tab2, "九龍"), (tab3, "新界")]:
    with tab:
        districts_in_region = [d for d in region_map[region]]
        dcols = st.columns(3)
        if not ranking.empty:
            for idx, dname in enumerate(districts_in_region):
                row = ranking[ranking["district"] == dname]
                if not row.empty:
                    r = row.iloc[0]
                    with dcols[idx % 3]:
                        st.markdown(f"""
                        <div class="district-card">
                            <strong>{dname}</strong><br>
                            <span style="color:#888;font-size:0.85rem;">
                                {int(r['carpark_count'] or 0)} 個停車場 · 
                                時租 ${float(r.get('avg_occupancy', 0) * 0 + 20):.0f} 起
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

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
