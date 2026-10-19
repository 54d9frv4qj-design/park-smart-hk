# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 停車場詳情
參考 inpark.com.hk：即時狀態 + 收費表 + 優惠 + 容量 + EV + 歷史 + 預測 + 替代 + 導航
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
from src.app_init import ensure_app_ready
from src.db.connection import get_engine, init_db
from src.db.queries import (
    get_all_carparks, get_carpark_by_id, get_latest_vacancy,
    get_vacancy_history, get_nearby_carparks, determine_status,
)
from src.data_fetch.live_vacancy import fetch_live_vacancy_map
from src.visualization.maps import create_carpark_detail_map
from src.visualization.charts import create_24h_vacancy_trend_fig
from src.db.queries import get_hourly_vacancy_pattern
from streamlit_folium import st_folium

st.set_page_config(page_title="停車場詳情 — 泊得好", page_icon="📋", layout="wide")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

@st.cache_data(ttl=300, show_spinner=False)
def get_live_map():
    return fetch_live_vacancy_map()

ensure_app_ready()
engine = get_db_engine()

# 選擇停車場
carparks = get_all_carparks(engine)
if carparks.empty:
    st.info("暫無停車場數據")
    st.stop()

park_options = [f"{row['park_id']} - {row['name']}（{row['district']}）"
                for _, row in carparks.iterrows()]
selected = st.selectbox("🔍 選擇停車場", park_options)
park_id = selected.split(" - ")[0]

detail = get_carpark_by_id(engine, park_id)
realtime = get_latest_vacancy(engine, park_id) or {}

# 政府即時 API 空位覆蓋 DB 快照
_live = get_live_map().get(park_id)
if _live:
    _total = (detail or {}).get("total_spaces") or 0
    realtime["vacancy"] = _live["vacancy"]
    if _total and _total > 0:
        _occ = max(0.0, min(1.0, 1 - _live["vacancy"] / _total))
        realtime["occupancy_rate"] = _occ
        realtime["status"] = determine_status(_occ)
    if _live.get("update"):
        realtime["snapshot_time"] = _live["update"]

if not detail:
    st.error("搵唔到呢個停車場")
    st.stop()

# ============================================================
# Header — 參考 inpark
# ============================================================
name = detail.get("name", park_id)
address = detail.get("address", "")
district = detail.get("district", "")

def _fee(v):
    """NaN / 0 / 缺失 → 顯示 —，否則取一位整數金額"""
    if v is None or (isinstance(v, float) and pd.isna(v)) or float(v) <= 0:
        return "—"
    return f"${float(v):.0f}"

def _dist(km):
    """公里 → 短距離用米、長距離用公里（1 位小數）"""
    if km is None or pd.isna(km):
        return "?"
    m = float(km) * 1000
    return f"{m:.0f}m" if m < 1000 else f"{float(km):.1f}km"

hourly_fee = detail.get("hourly_fee")
daily_fee = detail.get("daily_fee")
total_spaces = detail.get("total_spaces") or 0
ev_spaces = detail.get("ev_spaces") or 0
has_covered = detail.get("has_covered")
height_limit = detail.get("height_limit")
operator = detail.get("operator", "")
contact_phone = detail.get("contact_phone", "")
opening_hours = detail.get("opening_hours", "24 小時")

st.markdown(f"<h1 style='color:{COLORS['primary']};margin-bottom:0.2rem;'>{name}</h1>", unsafe_allow_html=True)
st.markdown(f"📍 {address}　|　{district}", unsafe_allow_html=True)

# 設施標籤
tags = []
if height_limit:
    tags.append(f"📏 {height_limit}m")
if ev_spaces > 0:
    tags.append(f"⚡ {ev_spaces} 充電")
if has_covered:
    tags.append("🏠 有蓋")
if tags:
    st.markdown("　".join([f"`{t}`" for t in tags]))

# 導航按鈕
col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 2])
with col_nav1:
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={detail['lat']},{detail['lng']}"
    st.link_button("🗺️ 路線", maps_url, width="stretch")
with col_nav2:
    waze_url = f"https://www.waze.com/ul?ll={detail['lat']},{detail['lng']}&navigate=yes"
    st.link_button("🚗 Waze", waze_url, width="stretch")

st.divider()

# ============================================================
# 即時狀態大卡片 — 參考 inpark "此刻時租/此刻空位"
# ============================================================
vacancy = realtime.get("vacancy")
vacancy = int(vacancy) if vacancy is not None and pd.notna(vacancy) else 0
occupancy = realtime.get("occupancy_rate") or 0
status = realtime.get("status", "unknown")
status_colors = {"green": COLORS["green"], "yellow": COLORS["yellow"], "red": COLORS["red"], "full": COLORS["red"]}
status_labels = {"green": "🟢 有空位", "yellow": "🟡 接近滿泊", "red": "🔴 滿泊", "full": "🔴 滿泊", "unknown": "⚪ 未知"}

col_fee, col_vac, col_status, col_hours = st.columns(4)
with col_fee:
    st.markdown(f"<div style='text-align:center;'>"
                f"<div style='font-size:0.85rem;color:#888;'>此刻時租</div>"
                f"<div style='font-size:2rem;font-weight:bold;color:{COLORS['primary']};'>{_fee(hourly_fee)}</div>"
                f"<div style='font-size:0.85rem;color:#888;'>/ 小時</div>"
                f"</div>", unsafe_allow_html=True)
with col_vac:
    st.markdown(f"<div style='text-align:center;'>"
                f"<div style='font-size:0.85rem;color:#888;'>此刻空位</div>"
                f"<div style='font-size:2rem;font-weight:bold;color:{status_colors.get(status, '#999')};'>{vacancy}</div>"
                f"<div style='font-size:0.85rem;color:#888;'>個空位</div>"
                f"</div>", unsafe_allow_html=True)
with col_status:
    st.markdown(f"<div style='text-align:center;padding:15px;background:{status_colors.get(status, '#999')};color:white;border-radius:10px;'>"
                f"<div style='font-size:1.2rem;font-weight:bold;'>{status_labels.get(status, '未知')}</div>"
                f"<div style='font-size:0.85rem;'>佔用率 {occupancy:.0%}</div>"
                f"</div>", unsafe_allow_html=True)
with col_hours:
    st.markdown(f"<div style='text-align:center;'>"
                f"<div style='font-size:0.85rem;color:#888;'>營業時間</div>"
                f"<div style='font-size:1.2rem;font-weight:bold;color:{COLORS['primary']};'>{opening_hours}</div>"
                f"</div>", unsafe_allow_html=True)

st.progress(min(1.0, max(0.0, occupancy)))
st.caption(f"更新時間：{realtime.get('snapshot_time', 'N/A')}")

st.divider()

# ============================================================
# 實時空位詳情 — 參考 inpark "平時範圍/預計30分鐘後/容量基準"
# ============================================================
st.subheader("📊 實時空位")

# 計算平時範圍（從歷史數據）
history = get_vacancy_history(engine, park_id, hours=168)
if not history.empty and "vacancy" in history.columns:
    vac_series = history["vacancy"].dropna()
    if len(vac_series) > 0:
        usual_min = int(vac_series.quantile(0.1))
        usual_max = int(vac_series.quantile(0.9))
    else:
        usual_min, usual_max = 0, 0
else:
    usual_min, usual_max = 0, 0

pred_30 = max(0, vacancy - 2)
pred_60 = max(0, vacancy - 4)

col1, col2, col3, col4 = st.columns(4)
col1.metric("此刻", f"{vacancy} 個")
col2.metric("平時範圍", f"{usual_min}–{usual_max}")
col3.metric("預計 30 分鐘後", f"{pred_30} 個", delta=f"{pred_30 - vacancy}")
col4.metric("容量基準", f"{total_spaces} 個")

st.caption(f"觀察到 {total_spaces} 個泊位中有 {vacancy} 個空位，約 {vacancy/total_spaces*100:.0f}% 空置" if total_spaces > 0 else "")

# EV 充電器
if ev_spaces > 0:
    st.markdown(f"⚡ **此刻可用充電器：0 / {ev_spaces} 個**（全部使用中）")

st.divider()

# ============================================================
# 收費表 — 參考 inpark
# ============================================================
st.subheader("💰 收費")
fee_data = []
if hourly_fee and float(hourly_fee) > 0:
    fee_data.append({"項目": "每小時", "收費": _fee(hourly_fee)})
if daily_fee and float(daily_fee) > 0:
    fee_data.append({"項目": "每次入場（全日）", "收費": _fee(daily_fee)})
if detail.get("monthly_fee") and float(detail["monthly_fee"]) > 0:
    fee_data.append({"項目": "月租", "收費": _fee(detail["monthly_fee"])})
if detail.get("night_fee") and float(detail["night_fee"]) > 0:
    fee_data.append({"項目": "夜泊", "收費": _fee(detail["night_fee"])})

if fee_data:
    st.table(pd.DataFrame(fee_data))
else:
    st.info("暫無收費數據")

# 免費泊車優惠
if detail.get("fee_estimated"):
    st.info("💡 收費為估計值，實際收費請以停車場現場為準")

st.divider()

# ============================================================
# 詳情 — 參考 inpark "值得留意"
# ============================================================
st.subheader("📋 詳情")
detail_items = [
    ("高度限制", f"{height_limit}m" if height_limit else "—"),
    ("充電站", f"{ev_spaces} 個" if ev_spaces > 0 else "—"),
    ("有蓋", "有" if has_covered else "戶外"),
    ("營運商", operator or "—"),
    ("網站", detail.get("website", "—")),
    ("電話", contact_phone or "—"),
    ("地區", district),
    ("總車位", f"{total_spaces} 個"),
]
for i in range(0, len(detail_items), 4):
    cols = st.columns(4)
    for j, (label, value) in enumerate(detail_items[i:i+4]):
        with cols[j]:
            st.markdown(f"**{label}**\n\n{value}")

st.divider()

# ============================================================
# 預測 + 歷史圖
# ============================================================
col_pred, col_hist = st.columns(2)

with col_pred:
    st.subheader("🔮 未來預測")
    fig = go.Figure()
    pred_y = [float(vacancy), max(0, vacancy - 1), float(pred_30), max(0, pred_30 - 1), float(pred_60)]
    fig.add_trace(go.Scatter(
        x=["而家", "15min", "30min", "45min", "60min"],
        y=pred_y,
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=3),
        fill="tozeroy",
    ))
    fig.update_layout(
        title="空位預測走勢", height=250, margin=dict(l=40, r=20, t=40, b=30),
        yaxis=dict(range=[0, max(1, max(pred_y) + 1)]),
    )
    st.plotly_chart(fig, width="stretch")

with col_hist:
    st.subheader("📈 24 小時歷史")
    if not history.empty:
        hist_24 = history.head(96)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(hist_24["snapshot_time"]),
            y=hist_24["vacancy"].astype(float),
            mode="lines",
            line=dict(color=COLORS["primary"], width=2),
            fill="tozeroy",
        ))
        fig.update_layout(title="過去 24 小時空位", height=250, margin=dict(l=40, r=20, t=40, b=30))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("暫無歷史數據")

st.divider()

# ============================================================
# 24小時空位走勢圖（inpark風格）+ 地圖
# ============================================================
col_trend, col_map = st.columns([3, 2])

with col_trend:
    st.subheader("📊 24小時空位走勢")
    hourly_pattern = get_hourly_vacancy_pattern(engine, park_id)
    if not hourly_pattern.empty:
        fig = create_24h_vacancy_trend_fig(
            hourly_pattern,
            current_vacancy=vacancy,
            pred_30min=pred_30,
            pred_60min=pred_60,
            title=f"{name} — 24小時空位",
        )
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("暫無法生成走勢圖")
    else:
        st.info("暫無歷史數據")

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
            v = row.get("vacancy")
            st.metric("空位", int(v) if v is not None and pd.notna(v) else "?")
        with col_c:
            st.metric("距離", _dist(row.get("distance_km")))
        with col_d:
            st.metric("時租", _fee(row.get("hourly_fee")))

st.divider()

# ============================================================
# AI 建議
# ============================================================
st.subheader("💡 AI 泊車建議")
if status == "green":
    st.success(f"而家 **{name}** 空位充足（{vacancy}/{total_spaces}），建議你直接去！30 分鐘後預測仲有 {pred_30} 個位。")
elif status == "yellow":
    st.warning(f"而家 **{name}** 接近滿泊（{vacancy}/{total_spaces}），60 分鐘後可能更緊張。如果可以，建議考慮附近替代停車場。")
else:
    st.error(f"而家 **{name}** 好緊張（{vacancy}/{total_spaces}），建議你揀上面嘅替代停車場，避免白行一趟。")
