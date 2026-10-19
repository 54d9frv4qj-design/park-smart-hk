# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 資料庫查詢函數庫
所有常用查詢集中管理，返回 dict 或 DataFrame
"""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import STATUS_THRESHOLDS


# ============================================================
# 停車場基本資料
# ============================================================
def get_all_carparks(engine: Engine) -> pd.DataFrame:
    """取得所有停車場基本資料"""
    query = text("SELECT * FROM carparks_static ORDER BY district, name")
    return pd.read_sql(query, engine)


def get_carpark_by_id(engine: Engine, park_id: str) -> Optional[dict]:
    """按 ID 取得停車場詳情"""
    query = text("SELECT * FROM carparks_static WHERE park_id = :pid")
    with engine.connect() as conn:
        row = conn.execute(query, {"pid": park_id}).mappings().first()
    return dict(row) if row else None


def get_carparks_by_district(engine: Engine, district: str) -> pd.DataFrame:
    """按地區取得停車場"""
    query = text(
        "SELECT * FROM carparks_static WHERE district = :d ORDER BY name"
    )
    return pd.read_sql(query, engine, params={"d": district})


def search_carparks(
    engine: Engine,
    keyword: str = "",
    district: str = "",
    vehicle_type: str = "privateCar",
) -> pd.DataFrame:
    """搜尋停車場（名稱/地址/地區），包含實時空位數據"""
    conditions = []
    params = {}
    if keyword:
        conditions.append("(name LIKE :kw OR address LIKE :kw OR name_en LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if district:
        conditions.append("district = :district")
        params["district"] = district

    where = " AND ".join(conditions) if conditions else "1=1"
    # 使用 v_carpark_status 視圖，包含實時空位同收費
    query = text(f"SELECT * FROM v_carpark_status WHERE {where} ORDER BY name LIMIT 100")
    return pd.read_sql(query, engine, params=params)


# ============================================================
# 實時空位
# ============================================================
def get_latest_vacancy(engine: Engine, park_id: str) -> Optional[dict]:
    """取得停車場最新實時空位"""
    query = text(
        "SELECT * FROM carparks_realtime WHERE park_id = :pid "
        "ORDER BY snapshot_time DESC LIMIT 1"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"pid": park_id}).mappings().first()
    return dict(row) if row else None


def get_all_latest_status(engine: Engine) -> pd.DataFrame:
    """取得所有停車場最新狀態（用於地圖）"""
    query = text("SELECT * FROM v_carpark_status ORDER BY district, name")
    return pd.read_sql(query, engine)


def get_vacancy_history(
    engine: Engine, park_id: str, hours: int = 24
) -> pd.DataFrame:
    """取得停車場過去 N 小時歷史空位"""
    since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    query = text(
        "SELECT snapshot_time, vacancy, occupancy_rate, status "
        "FROM carparks_realtime WHERE park_id = :pid AND snapshot_time >= :since "
        "ORDER BY snapshot_time"
    )
    return pd.read_sql(query, engine, params={"pid": park_id, "since": since})


def upsert_realtime_vacancy(engine: Engine, record: dict) -> None:
    """寫入或更新實時空位記錄"""
    query = text(
        """
        INSERT INTO carparks_realtime
            (park_id, snapshot_time, vacancy, vacancy_ev, occupancy_rate,
             status, data_source)
        VALUES
            (:park_id, :snapshot_time, :vacancy, :vacancy_ev, :occupancy_rate,
             :status, :data_source)
        """
    )
    with engine.connect() as conn:
        conn.execute(query, record)
        conn.commit()


# ============================================================
# 替代停車場推薦
# ============================================================
def get_nearby_carparks(
    engine: Engine,
    lat: float,
    lng: float,
    radius_km: float = 1.0,
    limit: int = 5,
) -> pd.DataFrame:
    """
    取得附近停車場（用 Haversine 公式計算距離）
    注意：SQLite 沒有內建 Haversine，這裡用簡化近似
    """
    # 先以經緯度範圍粗篩（1度≈111km）
    lat_range = radius_km / 111.0
    lng_range = radius_km / (111.0 * abs(__import__("math").cos(__import__("math").radians(lat))) + 0.001)

    query = text(
        """
        SELECT s.*, r.vacancy, r.occupancy_rate, r.status,
               ((s.lat - :lat) * (s.lat - :lat) +
                (s.lng - :lng) * (s.lng - :lng)) AS dist_sq
        FROM carparks_static s
        LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
        WHERE s.lat BETWEEN :lat_min AND :lat_max
          AND s.lng BETWEEN :lng_min AND :lng_max
        ORDER BY dist_sq ASC
        LIMIT :limit
        """
    )
    df = pd.read_sql(
        query, engine,
        params={
            "lat": lat, "lng": lng,
            "lat_min": lat - lat_range, "lat_max": lat + lat_range,
            "lng_min": lng - lng_range, "lng_max": lng + lng_range,
            "limit": limit,
        }
    )
    # 計算真實 Haversine 距離
    from src.utils.haversine import haversine_km
    if not df.empty:
        df["distance_km"] = df.apply(
            lambda r: haversine_km(lat, lng, r["lat"], r["lng"]), axis=1
        )
        df = df[df["distance_km"] <= radius_km].head(limit)
    return df


# ============================================================
# 咪錶
# ============================================================
def get_all_meters(engine: Engine) -> pd.DataFrame:
    """取得所有咪錶組"""
    query = text("SELECT * FROM metered_parking ORDER BY district, street_name")
    return pd.read_sql(query, engine)


def get_meter_latest_occupancy(engine: Engine, meter_id: str) -> Optional[dict]:
    """取得咪錶最新佔用"""
    query = text(
        "SELECT * FROM meter_occupancy WHERE meter_id = :mid "
        "ORDER BY snapshot_time DESC LIMIT 1"
    )
    with engine.connect() as conn:
        row = conn.execute(query, {"mid": meter_id}).mappings().first()
    return dict(row) if row else None


def get_all_meters_latest(engine: Engine) -> pd.DataFrame:
    """取得所有咪錶最新狀態"""
    query = text(
        """
        SELECT m.*, o.vacant_spaces, o.occupied_spaces, o.occupancy_rate,
               o.status, o.is_interpolated, o.snapshot_time
        FROM metered_parking m
        LEFT JOIN (
            SELECT meter_id, MAX(snapshot_time) as max_t
            FROM meter_occupancy GROUP BY meter_id
        ) latest ON m.meter_id = latest.meter_id
        LEFT JOIN meter_occupancy o
            ON m.meter_id = o.meter_id AND o.snapshot_time = latest.max_t
        ORDER BY m.district, m.street_name
        """
    )
    return pd.read_sql(query, engine)


def upsert_meter_occupancy(engine: Engine, record: dict) -> None:
    """寫入咪錶佔用記錄"""
    query = text(
        """
        INSERT INTO meter_occupancy
            (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
             occupancy_rate, status, is_interpolated, data_source)
        VALUES
            (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
             :occupancy_rate, :status, :is_interpolated, :data_source)
        """
    )
    with engine.connect() as conn:
        conn.execute(query, record)
        conn.commit()


# ============================================================
# 儀表板統計
# ============================================================
def get_overview_stats(engine: Engine) -> dict:
    """取得全港統計總覽"""
    query = text(
        """
        SELECT
            COUNT(DISTINCT s.park_id) AS total_carparks,
            COALESCE(SUM(s.total_spaces), 0) AS total_spaces,
            COALESCE(AVG(r.occupancy_rate), 0) AS avg_occupancy,
            COALESCE(SUM(CASE WHEN r.status = 'green' THEN 1 ELSE 0 END), 0) AS green_count,
            COALESCE(SUM(CASE WHEN r.status = 'yellow' THEN 1 ELSE 0 END), 0) AS yellow_count,
            COALESCE(SUM(CASE WHEN r.status IN ('red', 'full') THEN 1 ELSE 0 END), 0) AS red_count,
            (SELECT COUNT(*) FROM metered_parking) AS total_meters
        FROM carparks_static s
        LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
        """
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    return dict(row) if row else {}


def get_district_ranking(engine: Engine) -> pd.DataFrame:
    """取得 18 區排名（按平均空位率）"""
    query = text(
        """
        SELECT
            s.district,
            COUNT(s.park_id) AS carpark_count,
            SUM(s.total_spaces) AS total_spaces,
            AVG(r.occupancy_rate) AS avg_occupancy,
            AVG(r.vacancy) AS avg_vacancy
        FROM carparks_static s
        LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
        GROUP BY s.district
        ORDER BY avg_occupancy ASC
        """
    )
    return pd.read_sql(query, engine)


def get_timeseries_data(engine: Engine, days: int = 14) -> pd.DataFrame:
    """取得過去 N 天全港趨勢數據"""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    query = text(
        """
        SELECT
            DATE(snapshot_time) AS date,
            STRFTIME('%H', snapshot_time) AS hour,
            AVG(occupancy_rate) AS avg_occupancy,
            AVG(vacancy) AS avg_vacancy,
            COUNT(*) AS record_count
        FROM carparks_realtime
        WHERE snapshot_time >= :since
        GROUP BY DATE(snapshot_time), STRFTIME('%H', snapshot_time)
        ORDER BY date, hour
        """
    )
    return pd.read_sql(query, engine, params={"since": since})


def get_7x24_heatmap(engine: Engine) -> pd.DataFrame:
    """取得星期×小時佔用率熱力圖數據"""
    query = text(
        """
        SELECT
            CAST(STRFTIME('%w', snapshot_time) AS INTEGER) AS weekday,
            CAST(STRFTIME('%H', snapshot_time) AS INTEGER) AS hour,
            AVG(occupancy_rate) AS avg_occupancy
        FROM carparks_realtime
        GROUP BY weekday, hour
        ORDER BY weekday, hour
        """
    )
    df = pd.read_sql(query, engine)
    # 透視為 7×24 矩陣
    if not df.empty:
        pivot = df.pivot(index="weekday", columns="hour", values="avg_occupancy")
        pivot = pivot.reindex(index=range(7), columns=range(24))
        return pivot
    return pd.DataFrame()


# ============================================================
# 收費比較
# ============================================================
def get_fee_comparison(
    engine: Engine, district: str = "", sort_by: str = "hourly_fee"
) -> pd.DataFrame:
    """取得收費比較數據"""
    conditions = []
    params = {}
    if district:
        conditions.append("district = :district")
        params["district"] = district

    where = " AND ".join(conditions) if conditions else "1=1"
    order = "hourly_fee ASC" if sort_by == "hourly_fee" else f"{sort_by} ASC"
    query = text(
        f"SELECT park_id, name, district, total_spaces, hourly_fee, "
        f"daily_fee, monthly_fee, night_fee, is_government, fee_estimated "
        f"FROM carparks_static WHERE {where} AND hourly_fee IS NOT NULL "
        f"ORDER BY {order} LIMIT 200"
    )
    return pd.read_sql(query, engine, params=params)


# ============================================================
# 天氣
# ============================================================
def get_latest_weather(engine: Engine) -> Optional[dict]:
    """取得最新天氣數據"""
    query = text(
        "SELECT * FROM weather_data ORDER BY snapshot_time DESC LIMIT 1"
    )
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()
    return dict(row) if row else None


def upsert_weather(engine: Engine, record: dict) -> None:
    """寫入天氣記錄"""
    query = text(
        """
        INSERT INTO weather_data
            (snapshot_time, district, temperature, humidity, rainfall,
             weather_desc, has_warning, warning_type, uv_index)
        VALUES
            (:snapshot_time, :district, :temperature, :humidity, :rainfall,
             :weather_desc, :has_warning, :warning_type, :uv_index)
        """
    )
    with engine.connect() as conn:
        conn.execute(query, record)
        conn.commit()


# ============================================================
# 模型評估
# ============================================================
def save_model_evaluation(engine: Engine, record: dict) -> None:
    """保存模型評估結果"""
    query = text(
        """
        INSERT INTO model_evaluations
            (model_name, forecast_horizon, metric_name, metric_value,
             train_samples, test_samples, details)
        VALUES
            (:model_name, :forecast_horizon, :metric_name, :metric_value,
             :train_samples, :test_samples, :details)
        """
    )
    with engine.connect() as conn:
        conn.execute(query, record)
        conn.commit()


def get_model_evaluations(engine: Engine) -> pd.DataFrame:
    """取得所有模型評估記錄"""
    query = text(
        "SELECT * FROM model_evaluations ORDER BY evaluated_at DESC"
    )
    return pd.read_sql(query, engine)


# ============================================================
# 工具函數
# ============================================================
def determine_status(occupancy_rate: float) -> str:
    """根據佔用率判斷狀態顏色"""
    if occupancy_rate is None:
        return "unknown"
    vacancy_rate = 1 - occupancy_rate
    if vacancy_rate > STATUS_THRESHOLDS["green"]:
        return "green"
    elif vacancy_rate > STATUS_THRESHOLDS["yellow"]:
        return "yellow"
    else:
        return "red"
