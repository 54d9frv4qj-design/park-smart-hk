# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 實時地圖
參考 inpark.com.hk：地圖/列表切換 + 排序 + 價格 + 狀態標籤 + 篩選
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
from src.db.queries import get_all_latest_status, get_all_meters_latest
from src.visualization.maps import create_realtime_map, create_heatmap
from streamlit_folium import st_folium

st.set_page_config(page_title="實時地圖 — 泊得好", page_icon="🗺️", layout="wide")

st.markdown(f"<h1 style='color:{COLORS['primary']}'>🗺️ 全港實時地圖</h1>", unsafe_allow_html=True)
st.caption("點擊停車場標記查看詳情｜🟢有空位 🟡接近滿泊 🔴滿泊")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()

# 狀態標籤映射
STATUS_LABELS = {
    "green": ("🟢 有空位", COLORS["green"]),
    "yellow": ("🟡 接近滿泊", COLORS["yellow"]),
    "red": ("🔴 滿泊", COLORS["red"]),
    "full": ("🔴 滿泊", COLORS["red"]),
}

# 側邊欄篩選 — 參考 inpark
with st.sidebar:
    st.header("⚙️ 篩選")
    selected_district = st.selectbox("地區", ["全部"] + [d["name"] for d in HK_DISTRICTS])
    status_filter = st.multiselect("狀態", ["green", "yellow", "red", "full"],
                                   default=["green", "yellow", "red", "full"],
                                   format_func=lambda x: STATUS_LABELS.get(x, (x, ""))[0])
    fee_range = st.slider("時租範圍（HKD）", 0, 100, (0, 100))
    st.markdown("---")
    st.markdown("**設施**")
    filter_ev = st.checkbox("⚡ 有 EV 充電")
    filter_covered = st.checkbox("🏠 有蓋")
    filter_height = st.checkbox("📏 高度限制 > 2m")
    st.markdown("---")
    show_meters = st.checkbox("顯示路邊咪錶", value=False)
    map_type = st.radio("地圖類型", ["標記地圖", "熱力圖"])
    st.divider()
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

# 泊車時間選擇
duration_hours = st.selectbox("⏱️ 泊車時間", [1, 2, 3, 4, 8, 24],
                              format_func=lambda x: f"而家 · {x} 小時" if x < 24 else "全日",
                              index=0)

# 載入數據
all_status = get_all_latest_status(engine)
if not all_status.empty:
    df = all_status.copy()

    # 應用篩選
    if selected_district != "全部":
        df = df[df["district"] == selected_district]
    if status_filter:
        df = df[df["status"].isin(status_filter)]
    df = df[(df["hourly_fee"].fillna(0) >= fee_range[0]) & (df["hourly_fee"].fillna(0) <= fee_range[1])]

    # 設施篩選
    if filter_ev and "has_ev_charging" in df.columns:
        df = df[df["has_ev_charging"] == 1]
    if filter_covered and "has_covered" in df.columns:
        df = df[df["has_covered"] == 1]

    # 計算總價
    df["total_price"] = df["hourly_fee"].fillna(0) * duration_hours

    st.metric("顯示停車場數量", len(df))

    # 地圖/列表切換
    view_mode = st.radio("檢視方式", ["🗺️ 地圖", "📋 列表"], horizontal=True)

    carparks_list = df.to_dict("records")

    # 添加預測到 popup
    for cp in carparks_list:
        vac = cp.get("vacancy")
        if vac is not None and pd.notna(vac):
            v = int(vac)
            cp["prediction_30min"] = max(0, v - 2)
            cp["prediction_60min"] = max(0, v - 4)
        cp["total_price"] = float(cp.get("hourly_fee") or 0) * duration_hours

    meters_list = []
    if show_meters:
        meters_df = get_all_meters_latest(engine)
        if not meters_df.empty:
            if selected_district != "全部":
                meters_df = meters_df[meters_df["district"] == selected_district]
            meters_list = meters_df.to_dict("records")

    if view_mode == "🗺️ 地圖":
        if selected_district == "全部":
            # ===== 按區聚合顯示（18個標記）=====
            st.caption("💡 點擊側邊欄選擇地區，可查看該區嘅個別停車場位置")

            # 按區聚合統計（時租只統計有收費嘅，NULL/0 唔計入平均）
            def _avg_positive(s):
                vals = [v for v in s if pd.notna(v) and v > 0]
                return sum(vals) / len(vals) if vals else None
            def _count_positive(s):
                return sum(1 for v in s if pd.notna(v) and v > 0)

            district_stats = df.groupby("district").agg(
                carpark_count=("park_id", "count"),
                total_vacancy=("vacancy", "sum"),
                total_spaces=("total_spaces", "sum"),
                avg_lat=("lat", "mean"),
                avg_lng=("lng", "mean"),
                avg_fee=("hourly_fee", _avg_positive),
                fee_count=("hourly_fee", _count_positive),
                green_count=("status", lambda x: (x == "green").sum()),
                yellow_count=("status", lambda x: (x == "yellow").sum()),
                red_count=("status", lambda x: x.isin(["red", "full"]).sum()),
            ).reset_index()

            # 計算有位比率同狀態
            district_stats["vacancy_rate"] = district_stats["total_vacancy"] / district_stats["total_spaces"].replace(0, 1)
            district_stats["status"] = district_stats["vacancy_rate"].apply(
                lambda x: "green" if x > 0.2 else ("yellow" if x > 0.05 else "red")
            )

            # 生成區級標記
            district_points = []
            for _, row in district_stats.iterrows():
                vac = int(row["total_vacancy"]) if row["total_vacancy"] == int(row["total_vacancy"]) else row["total_vacancy"]
                total = int(row["total_spaces"]) if row["total_spaces"] == int(row["total_spaces"]) else row["total_spaces"]
                occ_rate = max(0.0, min(1.0, 1.0 - float(vac) / float(total))) if total else 0.0
                district_points.append({
                    "lat": row["avg_lat"],
                    "lng": row["avg_lng"],
                    "name": f"{row['district']}（{int(row['carpark_count'])}個停車場）",
                    "vacancy": vac,
                    "total_spaces": total,
                    "occupancy_rate": occ_rate,
                    "status": row["status"],
                    "hourly_fee": round(row["avg_fee"], 1) if pd.notna(row["avg_fee"]) else None,
                    "district": row["district"],
                })

            if map_type == "標記地圖":
                m = create_realtime_map(district_points, zoom=11)
            else:
                m = create_heatmap(district_points)
            st_folium(m, width="100%", height=550, returned_objects=[])

            # 各區統計表格
            st.subheader("📊 各區停車場統計")
            display_df = district_stats[[
                "district", "carpark_count", "total_spaces", "total_vacancy",
                "vacancy_rate", "green_count", "yellow_count", "red_count", "avg_fee"
            ]].copy()
            display_df.columns = ["地區", "停車場數", "總車位", "空位", "有位率", "🟢", "🟡", "🔴", "平均時租"]
            display_df["有位率"] = display_df["有位率"].apply(lambda x: f"{x:.0%}")
            display_df["平均時租"] = display_df["平均時租"].apply(lambda x: f"HK${x:.0f}" if pd.notna(x) else "—")
            display_df = display_df.sort_values("有位率", ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        else:
            # ===== 具體區：顯示個別停車場（唔受篩選影響，顯示全部）=====
            # 用未篩選嘅完整數據，確保該區所有停車場都顯示
            district_all = all_status[all_status["district"] == selected_district].copy()
            st.caption(f"📍 {selected_district} — 共 {len(district_all)} 個停車場")

            # 計算該區中心
            district_carparks = district_all.to_dict("records")
            for cp in district_carparks:
                vac = cp.get("vacancy")
                if vac is not None and pd.notna(vac):
                    v = int(vac)
                    cp["prediction_30min"] = max(0, v - 2)
                    cp["prediction_60min"] = max(0, v - 4)

            valid_coords = district_all[district_all["lat"].notna() & district_all["lng"].notna()]
            if not valid_coords.empty:
                center = (valid_coords["lat"].mean(), valid_coords["lng"].mean())
            else:
                center = (22.35, 114.13)

            # 該區咪錶
            district_meters = []
            if show_meters:
                meters_df_all = get_all_meters_latest(engine)
                if not meters_df_all.empty:
                    meters_df_d = meters_df_all[meters_df_all["district"] == selected_district]
                    district_meters = meters_df_d.to_dict("records")

            if map_type == "標記地圖":
                m = create_realtime_map(
                    district_carparks, center=center, zoom=13,
                    show_meters=show_meters, meters=district_meters,
                )
            else:
                m = create_heatmap(district_carparks, center=center, zoom=13)
            st_folium(m, width="100%", height=550, returned_objects=[])
    else:
        # 列表視圖 — 參考 inpark
        sort_by = st.radio("排序", ["最近", "最平"], horizontal=True)
        if sort_by == "最平":
            df = df.sort_values("total_price")
        else:
            df = df.sort_values("vacancy", ascending=False)

        st.markdown(f"**停車場及咪錶共 {len(df)} 個 · {duration_hours} 小時總價**")
        for _, row in df.head(50).iterrows():
            status_info = STATUS_LABELS.get(row["status"], ("⚪ 未知", "#999"))
            fee = float(row.get("hourly_fee") or 0)
            total = fee * duration_hours
            vac = row.get("vacancy")
            vac_str = f"{int(vac)} 個空位" if vac is not None and pd.notna(vac) else "暫無數據"

            st.markdown(f"""
            <div style="padding:0.8rem;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <strong>{row['name']}</strong>
                    <span style="color:#888;font-size:0.85rem;margin-left:0.5rem;">{row['district']}</span>
                    <br>
                    <span style="color:{status_info[1]};font-size:0.85rem;">{status_info[0]}</span>
                    <span style="color:#888;font-size:0.85rem;margin-left:1rem;">{vac_str}</span>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.2rem;font-weight:bold;color:{COLORS['primary']};">${total:.0f}</div>
                    <div style="font-size:0.8rem;color:#888;">總價 · {duration_hours} 小時</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 狀態統計
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    green = len(df[df["status"] == "green"])
    yellow = len(df[df["status"] == "yellow"])
    red = len(df[df["status"].isin(["red", "full"])])
    with col1:
        st.metric("🟢 有空位", green)
    with col2:
        st.metric("🟡 接近滿泊", yellow)
    with col3:
        st.metric("🔴 滿泊", red)
    with col4:
        avg_vac = df["vacancy"].dropna().mean()
        st.metric("平均空位", f"{avg_vac:.0f}" if pd.notna(avg_vac) else "N/A")
else:
    st.info("暫無數據，請先初始化資料庫")
