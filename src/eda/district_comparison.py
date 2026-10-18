# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 18 區對比分析
地區排名、供需對比、收費對比
"""
import pandas as pd
from sqlalchemy.engine import Engine

from src.utils.logger import log


def analyze_district_comparison(engine: Engine) -> pd.DataFrame:
    """18 區全面對比"""
    query = """
    SELECT
        s.district,
        COUNT(s.park_id) AS carpark_count,
        SUM(s.total_spaces) AS total_spaces,
        AVG(s.hourly_fee) AS avg_hourly_fee,
        AVG(r.occupancy_rate) AS avg_occupancy,
        AVG(r.vacancy) AS avg_vacancy,
        SUM(CASE WHEN r.status = 'green' THEN 1 ELSE 0 END) AS green_count,
        SUM(CASE WHEN r.status = 'yellow' THEN 1 ELSE 0 END) AS yellow_count,
        SUM(CASE WHEN r.status IN ('red', 'full') THEN 1 ELSE 0 END) AS red_count,
        SUM(CASE WHEN s.is_government = 1 THEN 1 ELSE 0 END) AS gov_count
    FROM carparks_static s
    LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
    GROUP BY s.district
    ORDER BY avg_occupancy DESC
    """
    df = pd.read_sql(query, engine)

    # 計算衍生指標
    df["vacancy_rate"] = 1 - df["avg_occupancy"]
    df["ease_score"] = df["vacancy_rate"] * 0.5 + (df["avg_vacancy"] / df["total_spaces"].max()) * 0.5
    df = df.sort_values("ease_score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    log.info(f"📊 18 區對比分析完成")
    return df


def get_most_available_districts(engine: Engine, top_n: int = 5) -> pd.DataFrame:
    """最易泊的地區 Top N"""
    df = analyze_district_comparison(engine)
    return df.head(top_n)[["rank", "district", "carpark_count", "avg_occupancy", "avg_vacancy"]]


def get_most_crowded_districts(engine: Engine, top_n: int = 5) -> pd.DataFrame:
    """最緊張的地區 Top N"""
    df = analyze_district_comparison(engine)
    return df.tail(top_n)[["rank", "district", "carpark_count", "avg_occupancy", "avg_vacancy"]]


def analyze_fee_by_district(engine: Engine) -> pd.DataFrame:
    """各地區收費對比"""
    query = """
    SELECT
        district,
        COUNT(*) AS carpark_count,
        AVG(hourly_fee) AS avg_hourly,
        MIN(hourly_fee) AS min_hourly,
        MAX(hourly_fee) AS max_hourly,
        AVG(daily_fee) AS avg_daily,
        AVG(monthly_fee) AS avg_monthly
    FROM carparks_static
    WHERE hourly_fee IS NOT NULL
    GROUP BY district
    ORDER BY avg_hourly DESC
    """
    df = pd.read_sql(query, engine)
    log.info(f"📊 地區收費對比完成")
    return df


def analyze_supply_demand(engine: Engine) -> pd.DataFrame:
    """供需分析：車位供給 vs 佔用需求"""
    query = """
    SELECT
        s.district,
        SUM(s.total_spaces) AS supply,
        AVG(r.occupancy_rate) AS demand_rate,
        SUM(s.total_spaces) * AVG(r.occupancy_rate) AS estimated_demand
    FROM carparks_static s
    LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
    GROUP BY s.district
    ORDER BY demand_rate DESC
    """
    df = pd.read_sql(query, engine)
    df["supply_demand_ratio"] = df["supply"] / (df["estimated_demand"] + 1)
    return df


def analyze_weather_impact(engine: Engine) -> pd.DataFrame:
    """天氣對空位的影響分析"""
    query = """
    SELECT
        CASE WHEN w.rainfall > 5 THEN '雨天'
             WHEN w.rainfall > 0 THEN '微雨'
             ELSE '晴天' END AS weather_type,
        AVG(r.occupancy_rate) AS avg_occupancy,
        AVG(r.vacancy) AS avg_vacancy,
        COUNT(*) AS record_count
    FROM carparks_realtime r
    JOIN weather_data w ON DATE(r.snapshot_time) = DATE(w.snapshot_time)
        AND ABS(STRFTIME('%H', r.snapshot_time) - STRFTIME('%H', w.snapshot_time)) < 2
    GROUP BY weather_type
    """
    try:
        df = pd.read_sql(query, engine)
        log.info(f"📊 天氣影響分析完成")
        return df
    except Exception as e:
        log.warning(f"⚠️ 天氣影響分析跳過：{e}")
        return pd.DataFrame()
