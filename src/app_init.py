# -*- coding: utf-8 -*-
"""App 啟動：從隨 repo 嘅壓縮 CSV 恢復 SQLite。"""
import sqlite3
import time
from pathlib import Path

import pandas as pd

from src.config import DB_PATH, PROJECT_ROOT
from src.utils.logger import log

CSV_EXPORT_DIR = PROJECT_ROOT / "data" / "csv_export"
CSV_TABLES = [
    "carparks_static",
    "carparks_realtime",
    "metered_parking",
    "meter_occupancy",
    "weather_data",
    "carpark_meter_nearby",
]
_initialized = False


def _st_status(msg: str):
    try:
        import streamlit as st
        if st.runtime.exists():
            st.text(f"⏳ {msg}")
            return
    except Exception:
        pass
    log.info(msg)


def is_db_ready() -> bool:
    if not DB_PATH.exists():
        return False
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        ok = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='carparks_static'"
        ).fetchone()
        n = conn.execute("SELECT COUNT(*) FROM carparks_static").fetchone()[0] if ok else 0
        conn.close()
        return n > 0
    except Exception:
        return False


def restore_from_csv_to_db(target_db_path: Path) -> bool:
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    _st_status("從 CSV 恢復資料庫...")
    start = time.time()
    try:
        conn = sqlite3.connect(str(target_db_path), timeout=30)
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = MEMORY")

        schema = (PROJECT_ROOT / "src" / "db" / "schema.sql").read_text(encoding="utf-8")
        for stmt in schema.split(";"):
            stmt = stmt.strip()
            if stmt and "create_hypertable" not in stmt.lower():
                try:
                    conn.execute(stmt)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        log.warning(f"Schema 警告: {e}")
        conn.commit()

        total = 0
        for table in CSV_TABLES:
            csv_path = CSV_EXPORT_DIR / f"{table}.csv.gz"
            if not csv_path.exists():
                continue
            try:
                conn.execute(f"DELETE FROM {table}")
                conn.commit()
            except Exception:
                pass
            df = pd.read_csv(csv_path, compression="gzip", encoding="utf-8-sig")
            if df.empty:
                continue
            for col in df.columns:
                df[col] = df[col].fillna(0 if df[col].dtype in ("float64", "int64") else "")
            df.to_sql(table, conn, if_exists="append", index=False, chunksize=20000)
            conn.commit()
            total += len(df)
            _st_status(f"  ✓ {table}: {len(df):,} 行")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_realtime_park_time ON carparks_realtime(park_id, snapshot_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_realtime_time ON carparks_realtime(snapshot_time)")
        conn.commit()
        conn.close()
        log.info(f"✅ CSV 恢復完成: {total:,} 行，用時 {time.time() - start:.1f}s")
        return True
    except Exception as e:
        log.error(f"CSV 恢復失敗: {e}")
        return False


def ensure_app_ready(force: bool = False) -> bool:
    global _initialized
    if _initialized and not force:
        return True
    if not force and is_db_ready():
        _initialized = True
        return True
    if restore_from_csv_to_db(DB_PATH):
        _initialized = True
        return True
    log.error("資料庫恢復失敗")
    return False
