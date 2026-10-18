# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 數據質量檢查
缺失值分析、異常值檢測、數據完整性報告
"""
import pandas as pd
from sqlalchemy.engine import Engine
from src.db.queries import get_all_carparks, get_all_meters
from src.utils.logger import log


def check_data_quality(engine: Engine) -> dict:
    """
    全面數據質量檢查
    返回：質量報告 dict
    """
    log.info("🔍 開始數據質量檢查...")
    report = {}

    # 1. 停車場靜態數據
    carparks = get_all_carparks(engine)
    report["carparks"] = _analyze_dataframe(carparks, "停車場靜態")

    # 2. 咪錶數據
    meters = get_all_meters(engine)
    report["meters"] = _analyze_dataframe(meters, "咪錶")

    # 3. 實時數據完整性
    with engine.connect() as conn:
        realtime_count = conn.execute(
            pd.read_sql("SELECT COUNT(*) as cnt FROM carparks_realtime", engine)
        ).scalar() if False else pd.read_sql(
            "SELECT COUNT(*) as cnt FROM carparks_realtime", engine
        )["cnt"].iloc[0]

        distinct_parks = pd.read_sql(
            "SELECT COUNT(DISTINCT park_id) as cnt FROM carparks_realtime", engine
        )["cnt"].iloc[0]

        time_range = pd.read_sql(
            "SELECT MIN(snapshot_time) as min_t, MAX(snapshot_time) as max_t FROM carparks_realtime",
            engine
        ).iloc[0]

    report["realtime"] = {
        "total_records": int(realtime_count),
        "distinct_parks": int(distinct_parks),
        "time_range": f"{time_range['min_t']} ~ {time_range['max_t']}",
        "avg_records_per_park": round(realtime_count / max(distinct_parks, 1), 1),
    }

    # 4. 異常值檢測
    report["anomalies"] = _detect_anomalies(carparks)

    log.info(f"✅ 數據質量檢查完成：{len(carparks)} 停車場，{realtime_count:,} 實時記錄")
    return report


def _analyze_dataframe(df: pd.DataFrame, name: str) -> dict:
    """分析單個 DataFrame 的質量"""
    if df.empty:
        return {"name": name, "status": "無數據"}

    total = len(df)
    missing = df.isnull().sum()
    missing_pct = (missing / total * 100).round(2)

    return {
        "name": name,
        "total_rows": total,
        "total_columns": len(df.columns),
        "missing_values": missing[missing > 0].to_dict(),
        "missing_pct": missing_pct[missing_pct > 0].to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "complete_rows": int(df.dropna().shape[0]),
    }


def _detect_anomalies(df: pd.DataFrame) -> list:
    """檢測異常值"""
    anomalies = []

    if "total_spaces" in df.columns:
        # 車位數異常（<10 或 >2000）
        weird_spaces = df[(df["total_spaces"] < 10) | (df["total_spaces"] > 2000)]
        if not weird_spaces.empty:
            anomalies.append({
                "type": "車位數異常",
                "count": len(weird_spaces),
                "details": weird_spaces[["park_id", "name", "total_spaces"]].head(5).to_dict("records"),
            })

    if "hourly_fee" in df.columns:
        # 收費異常（<5 或 >100）
        weird_fees = df[(df["hourly_fee"] < 5) | (df["hourly_fee"] > 100)]
        if not weird_fees.empty:
            anomalies.append({
                "type": "收費異常",
                "count": len(weird_fees),
                "details": weird_fees[["park_id", "name", "hourly_fee"]].head(5).to_dict("records"),
            })

    if "lat" in df.columns and "lng" in df.columns:
        # 經緯度超出香港範圍
        out_of_hk = df[
            (df["lat"] < 22.15) | (df["lat"] > 22.58) |
            (df["lng"] < 113.83) | (df["lng"] > 114.45)
        ]
        if not out_of_hk.empty:
            anomalies.append({
                "type": "經緯度超出香港",
                "count": len(out_of_hk),
                "details": out_of_hk[["park_id", "name", "lat", "lng"]].head(5).to_dict("records"),
            })

    return anomalies


def print_quality_report(report: dict) -> None:
    """印出數據質量報告"""
    print("\n" + "=" * 60)
    print("📊 數據質量檢查報告")
    print("=" * 60)

    for key, value in report.items():
        if isinstance(value, dict) and "name" in value:
            print(f"\n【{value['name']}】")
            print(f"  總行數：{value.get('total_rows', 'N/A')}")
            print(f"  總欄位：{value.get('total_columns', 'N/A')}")
            print(f"  完整行：{value.get('complete_rows', 'N/A')}")
            if value.get("missing_values"):
                print(f"  缺失值：{value['missing_values']}")
        elif key == "realtime":
            print(f"\n【實時數據】")
            print(f"  總記錄：{value['total_records']:,}")
            print(f"  停車場數：{value['distinct_parks']}")
            print(f"  每場平均：{value['avg_records_per_park']} 筆")
            print(f"  時間範圍：{value['time_range']}")
        elif key == "anomalies":
            print(f"\n【異常值檢測】")
            if value:
                for a in value:
                    print(f"  ⚠️ {a['type']}：{a['count']} 筆")
            else:
                print("  ✅ 未發現異常")

    print("\n" + "=" * 60)
