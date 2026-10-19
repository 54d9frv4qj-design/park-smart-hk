# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 將 DB 導出為壓縮 CSV
用於上傳 GitHub，App 首次運行時自動恢復
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.connection import get_engine

# 導出目錄
EXPORT_DIR = PROJECT_ROOT / "data" / "csv_export"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# 需要導出的表
TABLES = [
    "carparks_static",
    "carparks_realtime",
    "metered_parking",
    "meter_occupancy",
    "weather_data",
    "carpark_meter_nearby",
]


def export_to_csv():
    """將所有表導出為 .csv.gz"""
    engine = get_engine()
    total_size = 0

    for table in TABLES:
        print(f"導出 {table}...", end=" ", flush=True)
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        # 排除 AUTOINCREMENT 主鍵 id（恢復時自動生成，避免 UNIQUE 約束衝突）
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        out_path = EXPORT_DIR / f"{table}.csv.gz"
        df.to_csv(out_path, index=False, compression="gzip", encoding="utf-8-sig")
        size_mb = out_path.stat().st_size / 1024 / 1024
        total_size += size_mb
        print(f"{len(df):,} 行 → {size_mb:.1f} MB")

    print(f"\n✅ 全部導出完成！總大小: {total_size:.1f} MB")
    print(f"目錄: {EXPORT_DIR}")
    return total_size


if __name__ == "__main__":
    export_to_csv()
