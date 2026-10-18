# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 時段分佈分析
小時分佈、星期分佈、尖峰分析
"""
import pandas as pd
from sqlalchemy.engine import Engine

from src.utils.logger import log


def analyze_hourly_distribution(engine: Engine) -> pd.DataFrame:
    """分析每小時平均佔用率分佈"""
    query = """
    SELECT
        CAST(STRFTIME('%H', snapshot_time) AS INTEGER) AS hour,
        AVG(occupancy_rate) AS avg_occupancy,
        AVG(vacancy) AS avg_vacancy,
        COUNT(*) AS record_count
    FROM carparks_realtime
    GROUP BY hour
    ORDER BY hour
    """
    df = pd.read_sql(query, engine)
    log.info(f"📊 小時分佈分析完成：{len(df)} 個小時")
    return df


def analyze_weekday_distribution(engine: Engine) -> pd.DataFrame:
    """分析每星期平均佔用率"""
    query = """
    SELECT
        CAST(STRFTIME('%w', snapshot_time) AS INTEGER) AS weekday,
        AVG(occupancy_rate) AS avg_occupancy,
        AVG(vacancy) AS avg_vacancy,
        COUNT(*) AS record_count
    FROM carparks_realtime
    GROUP BY weekday
    ORDER BY weekday
    """
    df = pd.read_sql(query, engine)
    weekday_names = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
    df["weekday_name"] = df["weekday"].map(lambda x: weekday_names[x] if x < 7 else "?")
    log.info(f"📊 星期分佈分析完成")
    return df


def analyze_peak_hours(engine: Engine) -> dict:
    """分析尖峰時段"""
    hourly = analyze_hourly_distribution(engine)
    if hourly.empty:
        return {}

    # 最高佔用率的 3 個小時
    top_hours = hourly.nlargest(3, "avg_occupancy")
    # 最低佔用率的 3 個小時
    bottom_hours = hourly.nsmallest(3, "avg_occupancy")

    return {
        "peak_hours": top_hours[["hour", "avg_occupancy"]].to_dict("records"),
        "off_peak_hours": bottom_hours[["hour", "avg_occupancy"]].to_dict("records"),
        "peak_occupancy": round(top_hours["avg_occupancy"].max(), 4),
        "off_peak_occupancy": round(bottom_hours["avg_occupancy"].min(), 4),
        "peak_to_offpeak_ratio": round(
            top_hours["avg_occupancy"].max() / max(bottom_hours["avg_occupancy"].min(), 0.01), 2
        ),
    }


def analyze_weekday_vs_weekend(engine: Engine) -> dict:
    """比較週末與工作日"""
    query = """
    SELECT
        CASE WHEN CAST(STRFTIME('%w', snapshot_time) AS INTEGER) IN (0, 6)
             THEN '週末' ELSE '工作日' END AS day_type,
        AVG(occupancy_rate) AS avg_occupancy,
        AVG(vacancy) AS avg_vacancy
    FROM carparks_realtime
    GROUP BY day_type
    """
    df = pd.read_sql(query, engine)
    result = {}
    for _, row in df.iterrows():
        result[row["day_type"]] = {
            "avg_occupancy": round(row["avg_occupancy"], 4),
            "avg_vacancy": round(row["avg_vacancy"], 1),
        }
    return result


def get_7x24_heatmap_data(engine: Engine) -> pd.DataFrame:
    """取得 7×24 佔用率熱力圖數據"""
    query = """
    SELECT
        CAST(STRFTIME('%w', snapshot_time) AS INTEGER) AS weekday,
        CAST(STRFTIME('%H', snapshot_time) AS INTEGER) AS hour,
        AVG(occupancy_rate) AS avg_occupancy
    FROM carparks_realtime
    GROUP BY weekday, hour
    ORDER BY weekday, hour
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot(index="weekday", columns="hour", values="avg_occupancy")
    pivot = pivot.reindex(index=range(7), columns=range(24))
    pivot.index = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
    return pivot
