# -*- coding: utf-8 -*-
"""
app.py —— 香港智能停車 Streamlit Web App
=========================================
功能：
  1. 實時數據：點擊按鈕觸發後台抓取最新 API（停車場/咪錶/天氣）並寫入 SQLite
  2. 互動式地圖：streamlit-folium 顯示實時狀態地圖（綠=有位，紅=滿座），點擊看詳情
  3. 預測查詢：選擇地區/停車場，載入 .pkl 模型輸出未來 30/60 分鐘空位預測
  4. AI 建議：顯示 GenAI 生成的停車建議（需 OPENAI_API_KEY；無 Key 時用規則式）

啟動：streamlit run app.py
"""
from __future__ import annotations
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 路徑設定（讓 app.py 能 import src 套件）
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL_DIR, DB_PATH, OPENAI_MODEL
from src.data_fetch import carpark_api, meter_weather_api
from src.etl.etl_pipeline import run_etl
from src.db.db_writer import get_engine, init_db, write_to_db
from src.models.genai_advice import generate_parking_advice
from src.models import feature_engineering as fe

st.set_page_config(page_title="香港智能停車", page_icon="🅿️", layout="wide")


# ===========================================================================
# 工具：連線 / 快取
# ===========================================================================
@st.cache_resource
def get_db_engine():
    engine = get_engine()
    init_db(engine)
    return engine


@st.cache_data(ttl=60, show_spinner=False)
def load_latest_snapshot():
    """讀取數據庫中「最新」的空位快照，供地圖顯示。"""
    engine = get_db_engine()
    q = """
    SELECT s.park_id, s.name_tc AS name, s.district, s.latitude, s.longitude,
           r.vacancy, r.captured_at
    FROM carparks_static s
    LEFT JOIN (
        SELECT park_id, vacancy, captured_at
        FROM carparks_realtime cr
        WHERE category='HOURLY' AND vehicle_type='P'
          AND captured_at = (SELECT MAX(captured_at) FROM carparks_realtime cr2
                             WHERE cr2.park_id = cr.park_id
                               AND cr2.category='HOURLY' AND cr2.vehicle_type='P')
    ) r ON s.park_id = r.park_id
    WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
    """
    return pd.read_sql(q, engine)


@st.cache_data(ttl=60, show_spinner=False)
def load_weather_latest():
    engine = get_db_engine()
    q = """SELECT district, rainfall, humidity, temperature, captured_at
           FROM weather_and_events
           WHERE captured_at = (SELECT MAX(captured_at) FROM weather_and_events)"""
    return pd.read_sql(q, engine)


@st.cache_data(ttl=60, show_spinner=False)
def load_districts():
    engine = get_db_engine()
    return pd.read_sql("SELECT DISTINCT district FROM carparks_static "
                       "WHERE district IS NOT NULL ORDER BY district", engine)["district"].tolist()


# ===========================================================================
# 工具：抓取最新數據（寫庫）
# ===========================================================================
def refresh_realtime_data() -> int:
    """後台抓取最新 API 並寫入 SQLite，回傳寫入的停車場實時列數。"""
    raw = {}
    raw.update(carpark_api.fetch_carpark_all())
    raw.update(meter_weather_api.fetch_meter_all())
    raw["weather"] = meter_weather_api.fetch_weather()
    clean = run_etl(raw)
    engine = get_db_engine()
    write_to_db(engine, clean)
    # 清理快取，讓地圖/天氣顯示新數據
    load_latest_snapshot.clear()
    load_weather_latest.clear()
    load_districts.clear()
    return len(clean.get("carparks_realtime", pd.DataFrame()))


# ===========================================================================
# 工具：為指定停車場建立「目前時刻」的特徵向量（供模型預測）
# ===========================================================================
def build_current_features(park_id: str, district: str) -> pd.DataFrame:
    """根據最新歷史 + 天氣，組出模型需要的單行特徵向量。

    回傳的欄位與 feature_engineering.FEATURE_COLUMNS 一致（缺失補 0）。
    """
    engine = get_db_engine()
    now = pd.Timestamp.now()

    # 最新歷史空位（取最近 2 小時，頻率約 5 分鐘）
    hist = pd.read_sql(
        "SELECT captured_at, vacancy FROM carparks_realtime "
        "WHERE park_id=:pid AND category='HOURLY' AND vehicle_type='P' "
        "ORDER BY captured_at DESC LIMIT 24",
        engine, params={"pid": park_id})
    hist = hist.sort_values("captured_at")
    hist["captured_at"] = pd.to_datetime(hist["captured_at"])
    v = hist["vacancy"].astype(float).reset_index(drop=True)

    # 天氣（該區最新一筆）
    w = pd.read_sql(
        "SELECT rainfall, humidity, temperature FROM weather_and_events "
        "WHERE district=:d ORDER BY captured_at DESC LIMIT 1",
        engine, params={"d": district})
    rainfall = float(w["rainfall"].iloc[0]) if not w.empty else 0.0
    humidity = float(w["humidity"].iloc[0]) if not w.empty else 0.0
    temperature = float(w["temperature"].iloc[0]) if not w.empty else 0.0

    row = {
        "hour": now.hour, "dayofweek": now.dayofweek,
        "is_weekend": int(now.dayofweek >= 5),
        "is_peak": int((8 <= now.hour <= 10) or (17 <= now.hour <= 19)),
        "lag_15": float(v.iloc[-3]) if len(v) >= 3 else 0.0,
        "lag_30": float(v.iloc[-6]) if len(v) >= 6 else 0.0,
        "lag_60": float(v.iloc[-12]) if len(v) >= 12 else 0.0,
        "roll_30_mean": float(v.iloc[-6:].mean()) if len(v) >= 6 else float(v.mean()) if len(v) else 0.0,
        "roll_30_std": float(v.iloc[-6:].std()) if len(v) >= 6 else 0.0,
        "roll_60_mean": float(v.iloc[-12:].mean()) if len(v) >= 12 else float(v.mean()) if len(v) else 0.0,
        "roll_60_std": float(v.iloc[-12:].std()) if len(v) >= 12 else 0.0,
        "rainfall": rainfall, "humidity": humidity, "temperature": temperature,
    }
    return pd.DataFrame([row])


def predict_carpark(park_id: str, district: str, model_kind: str,
                    horizon_min: int = 30) -> dict:
    """對單一停車場做預測。

    Args:
        model_kind: 'classifier' 或 'regressor'
    Returns:
        {'prob_has_space': float 或 None, 'pred_vacancy': float 或 None, 'feat': DataFrame}
    """
    from joblib import load as jload
    path = MODEL_DIR / (f"{model_kind}_{horizon_min}min.pkl"
                        if model_kind == "classifier"
                        else f"regressor_{horizon_min}min.pkl")
    if not path.exists():
        return {"prob_has_space": None, "pred_vacancy": None, "feat": None}

    payload = jload(path)
    model = payload["model"]
    feature_cols = payload["feature_cols"]
    feat = build_current_features(park_id, district)
    # 只取模型訓練時用的欄位，並對齊順序
    X = feat.reindex(columns=feature_cols, fill_value=0.0)

    if model_kind == "classifier":
        prob = model.predict_proba(X)[0][1]
        return {"prob_has_space": float(prob), "pred_vacancy": None, "feat": feat}
    else:
        pred = model.predict(X)[0]
        return {"prob_has_space": None, "pred_vacancy": float(pred), "feat": feat}


# ===========================================================================
# 工具：互動地圖
# ===========================================================================
def make_status_map(snapshot: pd.DataFrame) -> "folium.Map":
    import folium
    from folium.plugins import MarkerCluster
    m = folium.Map(location=[22.3193, 114.1694], zoom_start=11,
                   tiles="OpenStreetMap")
    cluster = MarkerCluster().add_to(m)
    for _, r in snapshot.iterrows():
        v = r.get("vacancy")
        if v is None:
            color, status = "gray", "無資料"
        elif v > 0:
            color, status = "green", f"有位（{int(v)}）"
        else:
            color, status = "red", "滿座"
        popup = (f"<b>{r['name']}</b><br>分區：{r['district']}<br>"
                 f"狀態：{status}<br>更新：{r['captured_at']}")
        folium.CircleMarker(
            location=[r["latitude"], r["longitude"]], radius=7,
            color=color, fill=True, fill_color=color, fill_opacity=0.8,
            tooltip=f"{r['name']} — {status}", popup=folium.Popup(popup, max_width=260),
        ).add_to(cluster)
    return m


# ===========================================================================
# 主介面
# ===========================================================================
st.title("🅿️ 香港智能停車：車位預測與實時推薦")
st.caption("Data Science & AI Capstone —— 基於多源數據與時間序列的全港車位預測、咪錶整合與實時推薦")

# 側邊欄：實時數據控制
with st.sidebar:
    st.header("⚙️ 控制台")
    if st.button("🔄 抓取最新實時數據", use_container_width=True):
        with st.spinner("正在抓取停車場 / 咪錶 / 天氣 ..."):
            n = refresh_realtime_data()
        st.success(f"已寫入 {n} 列停車場實時數據")
        st.rerun()

    st.markdown("---")
    st.markdown("**模型狀態**")
    clf = MODEL_DIR / "classifier_30min.pkl"
    reg = MODEL_DIR / "regressor_30min.pkl"
    st.write("分類模型 (30min):", "✅ 就緒" if clf.exists() else "❌ 未訓練")
    st.write("回歸模型 (30min):", "✅ 就緒" if reg.exists() else "❌ 未訓練")
    if not clf.exists():
        st.info("尚未訓練模型。請在終端執行：`python run_pipeline.py --train`")

# 頂部：天氣概覽
w_now = load_weather_latest()
if not w_now.empty:
    cols = st.columns(4)
    avg_rain = w_now["rainfall"].mean()
    avg_hum = w_now["humidity"].mean()
    avg_temp = w_now["temperature"].mean()
    cols[0].metric("全港平均雨量 (mm/時)", f"{avg_rain:.1f}")
    cols[1].metric("平均濕度 (%)", f"{avg_hum:.0f}")
    cols[2].metric("平均氣溫 (°C)", f"{avg_temp:.1f}")
    cols[3].metric("更新時間", str(w_now["captured_at"].iloc[0])[11:16])

tab_map, tab_predict = st.tabs(["🗺️ 實時地圖", "🔮 預測與 AI 建議"])

# ---- Tab 1: 實時地圖 ----
with tab_map:
    st.subheader("全港停車場實時空位地圖")
    st.caption("綠 = 有位　紅 = 滿座　灰 = 無資料。點擊標記查看詳情。")
    snapshot = load_latest_snapshot()
    if snapshot.empty:
        st.warning("數據庫尚無停車場實時資料，請先在左側點擊「抓取最新實時數據」。")
    else:
        try:
            from streamlit_folium import st_folium
            st_folium(make_status_map(snapshot), width="100%", height=520)
        except ImportError:
            st.error("請安裝 streamlit-folium：pip install streamlit-folium")
        st.markdown("---")
        st.dataframe(snapshot[["name", "district", "vacancy", "captured_at"]]
                     .rename(columns={"name": "停車場", "district": "分區",
                                      "vacancy": "空位", "captured_at": "更新"}),
                     use_container_width=True)

# ---- Tab 2: 預測與 AI 建議 ----
with tab_predict:
    st.subheader("🔮 車位預測與 AI 停車建議")
    districts = load_districts()
    if not districts:
        st.warning("請先抓取數據以取得分區清單。")
    else:
        col1, col2, col3 = st.columns([2, 1, 1])
        district = col1.selectbox("選擇地區", districts)
        horizon = col2.selectbox("預測視窗", [30, 60], index=0)
        park_options = load_carparks_of(district)
        park_id = col3.selectbox("選擇停車場", list(park_options.keys()),
                                 format_func=lambda k: park_options[k])

        if st.button("🔮 執行預測", use_container_width=True):
            with st.spinner("正在預測 ..."):
                res_clf = predict_carpark(park_id, district, "classifier", horizon)
                res_reg = predict_carpark(park_id, district, "regressor", horizon)

            if res_clf["prob_has_space"] is None:
                st.warning(f"尚未找到 {horizon} 分鐘模型，請先執行 `python run_pipeline.py --train`。")
            else:
                prob = res_clf["prob_has_space"]
                pred = res_reg["pred_vacancy"]
                # 氣象條件
                wd = load_weather_latest()
                wx = None
                if not wd.empty:
                    m = wd[wd["district"] == district]
                    if not m.empty:
                        wx = m.iloc[0].to_dict()

                m1, m2, m3 = st.columns(3)
                m1.metric(f"未來 {horizon} 分鐘有位機率", f"{prob:.0%}")
                m2.metric(f"預測空位數", f"{pred:.0f}" if pred is not None else "N/A")
                m3.metric("評估", "充足" if (prob >= 0.7) else ("緊張" if prob >= 0.4 else "接近滿座"))

                # 該區替代停車場
                alts = get_alternatives(district, exclude_park_id=park_id)
                prediction = {
                    "pred_vacancy": pred if pred is not None else 0,
                    "prob_has_space": prob,
                    "horizon_min": horizon,
                    "carparks": [],
                }
                advice = generate_parking_advice(district, prediction, alts, wx)
                st.markdown("---")
                st.subheader("🤖 AI 停車建議")
                st.success(advice)

                st.caption("替代停車場（該區其他有空位的車場）")
                if alts:
                    st.dataframe(pd.DataFrame(alts)[
                        ["name", "district", "vacancy", "fee_per_hour_hkd"]
                    ].rename(columns={"name": "停車場", "district": "分區",
                                      "vacancy": "目前空位",
                                      "fee_per_hour_hkd": "時租(HKD)"}),
                        use_container_width=True)


@st.cache_data(ttl=60, show_spinner=False)
def load_carparks_of(district: str) -> dict:
    engine = get_db_engine()
    df = pd.read_sql("SELECT park_id, name_tc AS name FROM carparks_static "
                     "WHERE district=:d ORDER BY name_tc", engine, params={"d": district})
    return dict(zip(df["park_id"], df["name"]))


@st.cache_data(ttl=60, show_spinner=False)
def get_alternatives(district: str, exclude_park_id: str) -> list:
    engine = get_db_engine()
    q = """
    SELECT s.name_tc AS name, s.district, r.vacancy, NULL AS fee_per_hour_hkd
    FROM carparks_static s
    LEFT JOIN (SELECT park_id, vacancy, captured_at FROM carparks_realtime cr
               WHERE category='HOURLY' AND vehicle_type='P'
                 AND captured_at = (SELECT MAX(captured_at) FROM carparks_realtime cr2
                                    WHERE cr2.park_id=cr.park_id AND cr2.category='HOURLY'
                                      AND cr2.vehicle_type='P')) r ON s.park_id = r.park_id
    WHERE s.district=:d AND s.park_id<>:e AND r.vacancy > 0
    ORDER BY r.vacancy DESC LIMIT 5
    """
    df = pd.read_sql(q, engine, params={"d": district, "e": exclude_park_id})
    df["fee_per_hour_hkd"] = None
    return df.to_dict("records")
