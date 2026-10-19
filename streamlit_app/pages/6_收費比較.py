# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 收費比較
參考 inpark.com.hk：時長選擇 + 總價計算 + 篩選排序 + 最抵泊推薦
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.config import COLORS, HK_DISTRICTS
from src.db.connection import get_engine, init_db
from src.db.queries import get_fee_comparison
from src.visualization.heatmaps import create_fee_comparison_fig

st.set_page_config(page_title="收費比較 — 泊得好", page_icon="💰", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>💰 停車場收費比較</h1>", unsafe_allow_html=True)
st.caption("真實收費 + 估計收費｜幫你慳錢泊車")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()

# 泊車時間選擇 — 參考 inpark
duration_hours = st.selectbox("⏱️ 泊車時間", [1, 2, 3, 4, 8, 24],
                              format_func=lambda x: f"而家 · {x} 小時" if x < 24 else "全日",
                              index=0)

# 側邊欄篩選
with st.sidebar:
    st.header("⚙️ 篩選與排序")
    selected_district = st.selectbox("地區", ["全部"] + [d["name"] for d in HK_DISTRICTS])
    sort_by = st.selectbox("排序", ["總價（平→貴）", "總價（貴→平）", "時租（平→貴）", "日租（平→貴）"])
    only_gov = st.checkbox("只顯示政府停車場")
    only_estimated = st.checkbox("只顯示估計收費")
    fee_range = st.slider("時租範圍（HKD）", 0, 100, (0, 100))

# 載入數據
district = selected_district if selected_district != "全部" else ""
df = get_fee_comparison(engine, district=district, sort_by="hourly_fee")

if df.empty:
    st.info("暫無收費數據")
    st.stop()

# 計算總價 — 參考 inpark
df["total_price"] = df["hourly_fee"].fillna(0) * duration_hours

# 應用篩選
if only_gov:
    df = df[df["is_government"] == 1]
if only_estimated:
    df = df[df["fee_estimated"] == 1]
df = df[(df["hourly_fee"].fillna(0) >= fee_range[0]) & (df["hourly_fee"].fillna(0) <= fee_range[1])]

# 排序
if "總價（平→貴）" in sort_by:
    df = df.sort_values("total_price", ascending=True)
elif "總價（貴→平）" in sort_by:
    df = df.sort_values("total_price", ascending=False)
elif "時租" in sort_by:
    df = df.sort_values("hourly_fee", ascending=False if "貴→平" in sort_by else True)
elif "日租" in sort_by:
    df = df.sort_values("daily_fee", ascending=True)

# 統計
col1, col2, col3, col4 = st.columns(4)
col1.metric("停車場數", len(df))
col2.metric("政府場", int(df["is_government"].sum()))
col3.metric("平均總價", f"${df['total_price'].mean():.0f}" if not df.empty else "N/A")
col4.metric("平均時租", f"${df['hourly_fee'].mean():.0f}" if not df.empty else "N/A")

st.divider()

# 圖表
st.subheader(f"📊 收費分佈（{duration_hours} 小時總價）")
top20 = df.head(20)
fig = create_fee_comparison_fig(top20, title=f"頭 20 個停車場收費比較（{duration_hours} 小時）")
if fig:
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 表格 — 加入總價
st.subheader("📋 收費明細")
display = df[[
    "name", "district", "hourly_fee", "total_price", "daily_fee",
    "is_government", "fee_estimated"
]].copy()
display.columns = ["停車場", "地區", "時租", f"{duration_hours}小時總價", "日租", "政府場", "估計"]
display["政府場"] = display["政府場"].apply(lambda x: "✅" if x else "❌")
display["估計"] = display["估計"].apply(lambda x: "⚠️ 估計" if x else "✅ 真實")
st.dataframe(display, use_container_width=True, hide_index=True)

# 最抵泊推薦
st.divider()
st.subheader(f"💡 最抵泊推薦（{duration_hours} 小時）")
cheapest = df.nsmallest(3, "total_price")
for _, row in cheapest.iterrows():
    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
    with col_a:
        st.markdown(f"**{row['name']}**（{row['district']}）")
    with col_b:
        st.metric("時租", f"${row['hourly_fee']:.0f}")
    with col_c:
        st.metric(f"{duration_hours}小時總價", f"${row['total_price']:.0f}")
    with col_d:
        st.metric("日租", f"${row['daily_fee']:.0f}" if pd.notna(row['daily_fee']) and row['daily_fee'] else "N/A")

st.caption("⚠️ 標示「估計」的收費為模型推算，實際收費以停車場現場公佈為準")
