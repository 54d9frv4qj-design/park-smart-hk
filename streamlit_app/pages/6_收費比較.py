# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 收費比較
26 個政府場真實收費 + 581 個估計，並列時租/日租，篩選與排序
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import plotly.graph_objects as go

from src.config import COLORS, HK_DISTRICTS
from src.db.connection import get_engine, init_db
from src.db.queries import get_fee_comparison
from src.visualization.heatmaps import create_fee_comparison_fig

st.set_page_config(page_title="收費比較 — 泊得好", page_icon="💰", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>💰 停車場收費比較</h1>", unsafe_allow_html=True)
st.caption("26 個政府場真實收費 + 581 個估計收費｜幫你慳錢泊車")

@st.cache_resource
def get_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_engine()

# 側邊欄篩選
with st.sidebar:
    st.header("⚙️ 篩選與排序")
    selected_district = st.selectbox("地區", ["全部"] + [d["name"] for d in HK_DISTRICTS])
    sort_by = st.selectbox("排序", ["時租（平→貴）", "時租（貴→平）", "日租（平→貴）"])
    fee_type = st.multiselect("收費類型", ["時租", "日租", "夜泊", "月票"], default=["時租", "日租"])
    only_gov = st.checkbox("只顯示政府停車場")
    only_estimated = st.checkbox("只顯示估計收費")
    fee_range = st.slider("時租範圍（HKD）", 0, 100, (0, 100))

# 載入數據
district = selected_district if selected_district != "全部" else ""
df = get_fee_comparison(engine, district=district, sort_by="hourly_fee")

if df.empty:
    st.info("暫無收費數據")
    st.stop()

# 應用篩選
if only_gov:
    df = df[df["is_government"] == 1]
if only_estimated:
    df = df[df["fee_estimated"] == 1]
df = df[(df["hourly_fee"].fillna(0) >= fee_range[0]) & (df["hourly_fee"].fillna(0) <= fee_range[1])]

if "貴→平" in sort_by:
    df = df.sort_values("hourly_fee", ascending=False)
elif "日租" in sort_by:
    df = df.sort_values("daily_fee", ascending=True)

# 統計
col1, col2, col3, col4 = st.columns(4)
col1.metric("停車場數", len(df))
col2.metric("政府場", int(df["is_government"].sum()))
col3.metric("估計收費", int(df["fee_estimated"].sum()))
col4.metric("平均時租", f"HK${df['hourly_fee'].mean():.0f}" if not df.empty else "N/A")

st.divider()

# 圖表
st.subheader("📊 收費分佈")
top20 = df.head(20)
fig = create_fee_comparison_fig(top20, title="頭 20 個停車場收費比較")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# 表格
st.subheader("📋 收費明細")
display = df[[
    "name", "district", "hourly_fee", "daily_fee", "monthly_fee",
    "night_fee", "is_government", "fee_estimated"
]].copy()
display.columns = ["停車場", "地區", "時租(HKD)", "日租(HKD)", "月票(HKD)", "夜泊(HKD)", "政府場", "估計"]
display["政府場"] = display["政府場"].apply(lambda x: "✅" if x else "❌")
display["估計"] = display["估計"].apply(lambda x: "⚠️ 估計" if x else "✅ 真實")
st.dataframe(display, use_container_width=True, hide_index=True)

# 最抵泊推薦
st.divider()
st.subheader("💡 最抵泊推薦")
cheapest = df.nsmallest(3, "hourly_fee")
for _, row in cheapest.iterrows():
    col_a, col_b, col_c = st.columns([3, 1, 1])
    with col_a:
        st.markdown(f"**{row['name']}**（{row['district']}）")
    with col_b:
        st.metric("時租", f"HK${row['hourly_fee']:.0f}")
    with col_c:
        st.metric("日租", f"HK${row['daily_fee']:.0f}" if row['daily_fee'] else "N/A")

st.caption("⚠️ 標示「估計」的收費為模型推算，實際收費以停車場現場公佈為準")
