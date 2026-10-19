# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 儀表板
全港統計 + 地區排名
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.config import COLORS
from src.app_init import ensure_app_ready
from src.db.connection import get_engine, init_db
from src.db.queries import get_overview_stats, get_district_ranking
from src.visualization.heatmaps import create_district_ranking_fig

st.set_page_config(page_title="儀表板 — 泊得好", page_icon="📊", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>📊 數據儀表板</h1>", unsafe_allow_html=True)

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

ensure_app_ready()
engine = get_db_engine()

# ============================================================
# 全港統計
# ============================================================
st.subheader("📈 全港統計")
stats = get_overview_stats(engine)
col1, col2, col3, col4 = st.columns(4)
col1.metric("停車場總數", f"{int(stats.get('total_carparks') or 0):,}")
col2.metric("總車位", f"{int(stats.get('total_spaces') or 0):,}")
col3.metric("平均佔用率", f"{float(stats.get('avg_occupancy') or 0):.1%}")
col4.metric("充足/偏緊/滿座", f"{int(stats.get('green_count') or 0)}/{int(stats.get('yellow_count') or 0)}/{int(stats.get('red_count') or 0)}")

st.divider()

# ============================================================
# 地區排名
# ============================================================
st.subheader("🏆 18 區排名（由易泊到緊張）")
ranking = get_district_ranking(engine)
if not ranking.empty:
    fig = create_district_ranking_fig(ranking, value_col="avg_occupancy", ascending=True)
    st.plotly_chart(fig, width="stretch")

    # 表格
    display = ranking[["district", "carpark_count", "total_spaces", "avg_occupancy", "avg_vacancy"]].copy()
    display.columns = ["地區", "停車場數", "總車位", "平均佔用率", "平均空位"]
    display["平均佔用率"] = display["平均佔用率"].apply(lambda x: f"{x:.1%}")
    st.dataframe(display, width="stretch", hide_index=True)
else:
    st.info("暫無地區排名數據")
