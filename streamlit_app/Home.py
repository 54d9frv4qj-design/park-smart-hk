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

from src.config import COLORS, APP_NAME
from src.app_init import ensure_app_ready
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_overview_stats, get_all_latest_status,
    get_district_ranking, overlay_live_vacancy,
)
from src.data_fetch.live_vacancy import fetch_live_vacancy_map
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

@st.cache_data(ttl=300, show_spinner=False)
def get_live_map():
    return fetch_live_vacancy_map()

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
# Hero 區 — 品牌標題
# ============================================================
st.markdown('<div class="hero-title">🅿️ 泊得好 Park Smart HK</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">香港智能泊車 — 實時空位、收費、預測，出發前心中有數</div>', unsafe_allow_html=True)

st.divider()

# ============================================================
# 統計卡
# ============================================================
st.subheader("📊 全港即時統計")
stats = get_overview_stats(engine)
# DB 快照 + 政府即時 API 空位覆蓋，平均佔用率用即時值
live_df = overlay_live_vacancy(get_all_latest_status(engine), get_live_map())
live_occ = live_df["occupancy_rate"].dropna().mean()
if pd.notna(live_occ):
    stats["avg_occupancy"] = live_occ
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
    if not live_df.empty:
        carparks_list = live_df.to_dict("records")
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
                    fee = r.get("avg_fee")
                    fee_txt = f"時租 HK${float(fee):.0f} 起" if pd.notna(fee) and float(fee) > 0 else "時租資料待補"
                    with dcols[idx % 3]:
                        st.markdown(f"""
                        <div class="district-card">
                            <strong>{dname}</strong><br>
                            <span style="color:#888;font-size:0.85rem;">
                                {int(r['carpark_count'] or 0)} 個停車場 · {fee_txt}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

# ============================================================
# 側邊欄 — 品牌（左上角），頁面導航由 Streamlit 自動提供
# ============================================================
with st.sidebar:
    st.markdown(f"### 🅿️ {APP_NAME}")
    st.caption("香港智能泊車")
    st.markdown("---")
    st.caption("更新：每 10 分鐘自動刷新")
