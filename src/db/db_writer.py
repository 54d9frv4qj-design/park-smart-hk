# -*- coding: utf-8 -*-
"""
db_writer.py —— SQLAlchemy 連線 + 寫入 SQLite
===============================================
讀取 schema.sql 建立四張表，再把清洗後的 DataFrame 寫入數據庫。

寫入策略：
  * carparks_static     -> 主鍵衝突時更新（upsert）
  * carparks_realtime   -> append（保留歷史，供時間序列建模）
  * metered_parking     -> 主鍵衝突時更新（咪錶位是固定集合）
  * weather_and_events  -> append（保留歷史）
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..config import DB_PATH, SCHEMA_SQL_PATH


def get_engine(db_path: Optional[Path] = None) -> Engine:
    """建立 SQLite 引擎（check_same_thread=False 以便多執行緒/Streamlit 使用）。"""
    path = db_path or DB_PATH
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def init_db(engine: Engine, schema_path: Optional[Path] = None) -> None:
    """執行 schema.sql 建立表格（IF NOT EXISTS，重複執行安全）。

    用 sqlite3 原生 executescript 執行整份多重語句的 schema
    （SQLAlchemy 的 text() 一次只能跑一句，不適合整份 SQL 檔）。
    """
    schema = (schema_path or SCHEMA_SQL_PATH).read_text(encoding="utf-8")
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.executescript(schema)
        raw.commit()
    finally:
        raw.close()
    print("[DB] 資料庫已初始化/確認結構")


def _upsert(engine: Engine, table: str, df: pd.DataFrame, key_col: str) -> None:
    """以 SQLAlchemy 寫入，並在主鍵衝突時做 INSERT OR REPLACE（upsert）。

    只寫入「目標表已存在」的欄位（交集），避免清洗後多出來的欄位造成
    "no such column" 錯誤。
    """
    if df.empty:
        print(f"[DB] {table}: 空表，跳過")
        return
    # 取得目標表現有欄位
    with engine.connect() as conn:
        table_cols = set(row[1] for row in conn.execute(
            text(f"PRAGMA table_info({table})")).fetchall())
    cols = [c for c in df.columns if c in table_cols]
    if not cols:
        print(f"[DB] {table}: 無可寫入欄位，跳過")
        return

    # 將 DataFrame 寫入暫存記憶體表，再以 SQL 搬進目標表，
    # 以取得完整的「衝突時取代」語意（SQLite 不支援標準 MERGE）。
    temp_table = f"_{table}_staging"
    sub = df[cols]
    with engine.begin() as conn:
        sub.to_sql(temp_table, conn, if_exists="replace", index=False)
        quoted = ", ".join(f'"{c}"' for c in cols)
        conn.execute(text(
            f"INSERT OR REPLACE INTO {table} ({quoted}) SELECT {quoted} FROM {temp_table}"
        ))
        conn.execute(text(f"DROP TABLE {temp_table}"))
    print(f"[DB] upsert {table}: {len(sub)} 列")


def _append(engine: Engine, table: str, df: pd.DataFrame) -> None:
    """直接 append 寫入（保留歷史）。"""
    if df.empty:
        print(f"[DB] {table}: 空表，跳過")
        return
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"[DB] append {table}: {len(df)} 列")


def write_to_db(engine: Engine, clean: Dict[str, pd.DataFrame]) -> None:
    """把清洗後的 DataFrame dict 寫入對應表格。

    Args:
        engine: 由 get_engine 建立的引擎
        clean:  由 etl.run_etl 回傳的 {表名: DataFrame} dict
    """
    if not clean.get("carparks_static").empty:
        _upsert(engine, "carparks_static", clean["carparks_static"], "park_id")
    if not clean.get("carparks_realtime").empty:
        # 實時表有 (park_id, captured_at, vehicle_type, category) 複合 UNIQUE；
        # 用 upsert(INSERT OR REPLACE) 避免重複執行時因同快照而報錯
        _upsert(engine, "carparks_realtime", clean["carparks_realtime"], None)
    if not clean.get("metered_parking_dist").empty:
        # 把咪錶分佈 + 佔用合併成單一 metered_parking 表
        _write_metered(engine, clean)
    if not clean.get("weather").empty:
        _append(engine, "weather_and_events", clean["weather"])


def _write_metered(engine: Engine, clean: Dict[str, pd.DataFrame]) -> None:
    """把咪錶分佈與佔用合併成 metered_parking 表。

    分佈是靜態主體，佔用是即時狀態；以 ParkingSpaceId 做 outer join。
    """
    dist = clean["metered_parking_dist"]
    occ = clean["metered_parking_occ"]

    # 統一名稱欄位
    dist = dist.rename(columns={
        "ParkingSpaceId": "parking_space_id",
        "PoleId": "pole_id",
        "Region": "region_raw",
        "VehicleType": "vehicle_type",
        "LPP": "lpp_min",
        "TimeUnit": "time_unit_min",
        "PaymentUnit": "payment_unit_hkd",
        "OperatingPeriod": "operating_period",
    })
    occ = occ.rename(columns={
        "ParkingSpaceId": "parking_space_id",
        "meter_status": "meter_status",
        "is_vacant": "is_vacant",
        "captured_at": "occupancy_changed",
    })
    # 清洗後可能同時存在原名與正則化名（如 ParkingSpaceId 與 parking_space_id），去重
    dist = dist.loc[:, ~dist.columns.duplicated()]
    occ = occ.loc[:, ~occ.columns.duplicated()]

    if occ.empty:
        occ = pd.DataFrame({"parking_space_id": []})

    merged = dist.merge(
        occ[["parking_space_id", "meter_status", "is_vacant", "occupancy_changed"]],
        on="parking_space_id", how="left")

    merged["is_vacant"] = merged["is_vacant"].fillna(1).astype(int)
    merged["meter_status"] = merged["meter_status"].fillna("N")
    merged["captured_at"] = pd.Timestamp.now()
    merged = merged.drop(columns=["region_raw"], errors="ignore")

    _upsert(engine, "metered_parking", merged, "parking_space_id")
