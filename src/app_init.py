# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — App 啟動初始化
數據來源優先級：
1. 已有 DB → 直接用
2. CSV 導出檔（data/csv_export/*.csv.gz）→ 從 CSV 恢復
3. 真實數據目錄（本地）→ 導入真實數據
4. 以上都冇 → 生成模擬數據

Streamlit Cloud 上 /tmp/ 係臨時檔案系統，每次重新部署都要重建 DB。
使用「臨時 DB + 原子重命名」避免並發寫入衝突。
"""
import os
import sqlite3
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.config import STREAMLIT_CLOUD, DB_PATH, PROJECT_ROOT
from src.db.connection import get_engine, init_db
from src.utils.logger import log

# 真實數據目錄（本地先有，Streamlit Cloud 冇）
REAL_DATA_DIR = Path(os.getenv(
    "REAL_DATA_DIR",
    r"C:\Users\Administrator\Downloads\data\https%3A%2F%2Fresource.data.one.gov.hk%2Ftd%2Fcarpark%2F"
))

# CSV 導出目錄（隨 GitHub 上傳，Streamlit Cloud 都有）
CSV_EXPORT_DIR = PROJECT_ROOT / "data" / "csv_export"

# 需要從 CSV 恢復的表（按依賴順序）
CSV_TABLES = [
    "carparks_static",
    "carparks_realtime",
    "metered_parking",
    "meter_occupancy",
    "weather_data",
    "carpark_meter_nearby",
]

# 模組級標誌：防止同一進程重複初始化
_initialized = False


def _st_status(msg: str):
    """Streamlit 環境下顯示狀態，否則用 log"""
    try:
        import streamlit as st
        if st.runtime.exists():
            st.text(f"⏳ {msg}")
            return
    except Exception:
        pass
    log.info(msg)


def is_db_ready(db_path: Path = None) -> bool:
    """檢查 DB 是否已就緒（檔案存在 + 有數據）"""
    path = db_path or DB_PATH
    if not path.exists():
        return False
    try:
        conn = sqlite3.connect(str(path), timeout=5)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='carparks_static'"
        ).fetchone()
        if not result:
            conn.close()
            return False
        count = conn.execute("SELECT COUNT(*) FROM carparks_static").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def has_csv_export() -> bool:
    """檢查 CSV 導出檔案是否存在"""
    if not CSV_EXPORT_DIR.exists():
        return False
    return (CSV_EXPORT_DIR / "carparks_static.csv.gz").exists()


def _fast_csv_to_sqlite(csv_path: Path, table_name: str, conn: sqlite3.Connection):
    """
    快速將 CSV 導入 SQLite
    使用 PRAGMA 優化 + 單一事務 + 大批量插入
    """
    df = pd.read_csv(csv_path, compression="gzip", encoding="utf-8-sig")
    if df.empty:
        return 0

    # 用 to_sql 配合優化後的連接
    df.to_sql(
        table_name, conn,
        if_exists="append", index=False,
        chunksize=20000,
    )
    return len(df)


def restore_from_csv_to_db(target_db_path: Path) -> bool:
    """
    從 CSV 導出檔案恢復 DB 到指定路徑
    使用臨時路徑寫入，完成後原子重命名
    """
    tmp_path = target_db_path.with_suffix(".tmp.db")
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except Exception:
            pass

    _st_status("從 CSV 恢復資料庫（約 20 秒）...")
    start = time.time()

    try:
        # 用原生 sqlite3 + PRAGMA 優化，速度比 SQLAlchemy 快 5-10 倍
        conn = sqlite3.connect(str(tmp_path), timeout=30)
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA cache_size = -64000")
        conn.execute("PRAGMA locking_mode = EXCLUSIVE")

        # 執行 schema
        schema_path = PROJECT_ROOT / "src" / "db" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            if "create_hypertable" in stmt.lower():
                continue
            try:
                conn.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    log.warning(f"Schema 警告: {e}")
        conn.commit()

        # 逐表導入
        total_rows = 0
        for table in CSV_TABLES:
            csv_path = CSV_EXPORT_DIR / f"{table}.csv.gz"
            if not csv_path.exists():
                log.warning(f"  跳過 {table}（檔案唔存在）")
                continue

            t0 = time.time()
            rows = _fast_csv_to_sqlite(csv_path, table, conn)
            conn.commit()
            elapsed = time.time() - t0
            total_rows += rows
            _st_status(f"  ✓ {table}: {rows:,} 行 ({elapsed:.1f}s)")

        # 建立索引（如果 schema 冇自動建立）
        conn.execute("CREATE INDEX IF NOT EXISTS idx_realtime_park_time ON carparks_realtime(park_id, snapshot_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_realtime_time ON carparks_realtime(snapshot_time)")
        conn.commit()

        conn.close()

        # 原子重命名
        if target_db_path.exists():
            target_db_path.unlink()
        tmp_path.rename(target_db_path)

        elapsed = time.time() - start
        log.info(f"✅ CSV 恢復完成: {total_rows:,} 行，用時 {elapsed:.1f}s")
        return True

    except Exception as e:
        log.error(f"CSV 恢復失敗: {e}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return False


def has_real_data() -> bool:
    """檢查真實數據目錄是否存在並有 JSON 檔案"""
    if not REAL_DATA_DIR.exists():
        return False
    json_files = list(REAL_DATA_DIR.glob("*vacancy_all.json"))
    return len(json_files) > 10


def _add_auxiliary_data(engine):
    """補充咪錶、天氣、空間匹配數據"""
    try:
        from src.mock_data.meter_generator import generate_mock_meters
        from src.mock_data.weather_generator import generate_mock_weather
        from src.etl.spatial_join import build_carpark_meter_nearby

        _st_status("生成咪錶數據...")
        generate_mock_meters(engine, count=200, days=14)

        _st_status("生成天氣數據...")
        generate_mock_weather(engine, days=14)

        _st_status("建立空間匹配...")
        build_carpark_meter_nearby(engine, radius_km=2.0)

        log.info("✅ 附加數據生成完成")
    except Exception as e:
        log.warning(f"附加數據生成失敗（唔影響主要功能）: {e}")


def _build_with_mock_data(target_db_path: Path) -> bool:
    """用模擬數據生成器建立 DB"""
    tmp_path = target_db_path.with_suffix(".tmp.db")
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except Exception:
            pass

    _st_status("生成模擬數據（約 30 秒）...")
    try:
        from sqlalchemy import create_engine
        tmp_engine = create_engine(
            f"sqlite:///{tmp_path}",
            connect_args={"check_same_thread": False},
        )
        init_db(tmp_engine)

        from src.mock_data.carpark_generator import generate_mock_carparks
        generate_mock_carparks(tmp_engine, count=607, days=14)
        _add_auxiliary_data(tmp_engine)

        tmp_engine.dispose()
        if target_db_path.exists():
            target_db_path.unlink()
        tmp_path.rename(target_db_path)
        log.info("✅ 模擬數據 DB 建立完成")
        return True
    except Exception as e:
        log.error(f"模擬數據生成失敗: {e}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return False


def ensure_app_ready(force: bool = False) -> bool:
    """
    確保 App 就緒：DB 存在 + 有數據

    策略：
    1. 檢查 DB 是否已就緒 → 直接用
    2. 檢查有冇其他進程正在初始化（臨時檔案存在）→ 等待
    3. 自己開始初始化（用臨時 DB + 原子重命名）
    4. 數據來源優先級：CSV → 真實數據 → 模擬數據
    """
    global _initialized

    # 快速路徑：同進程已初始化
    if _initialized and not force:
        return True

    # 快速路徑：DB 已就緒
    if not force and is_db_ready():
        _initialized = True
        return True

    # 檢查有冇其他進程正在初始化
    tmp_path = DB_PATH.with_suffix(".tmp.db")
    wait_count = 0
    while tmp_path.exists() and wait_count < 90:
        try:
            mtime = tmp_path.stat().st_mtime
            if time.time() - mtime > 120:
                log.warning("臨時 DB 過期（>2分鐘），清理後重新初始化")
                tmp_path.unlink(missing_ok=True)
                break
        except Exception:
            pass
        _st_status(f"等待其他進程初始化... ({wait_count}s)")
        time.sleep(1)
        wait_count += 1
        if is_db_ready():
            _initialized = True
            return True

    # 開始初始化
    log.info(f"初始化資料庫到 {DB_PATH}...")

    if force and DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except Exception:
            pass

    # 優先級 1：從 CSV 恢復
    if has_csv_export():
        if restore_from_csv_to_db(DB_PATH):
            _initialized = True
            return True
        log.warning("CSV 恢復失敗，嘗試其他數據源...")

    # 優先級 2：真實數據（本地先有）
    if has_real_data() and not STREAMLIT_CLOUD:
        _st_status("導入真實數據...")
        try:
            engine = get_engine()
            init_db(engine)
            from scripts.import_real_data import import_real_data
            result = import_real_data(data_dir=REAL_DATA_DIR)
            log.info(f"真實數據導入完成: {result['carparks']} 停車場")
            _add_auxiliary_data(engine)
            _initialized = True
            return True
        except Exception as e:
            log.error(f"真實數據導入失敗，降級模擬數據: {e}")

    # 優先級 3：模擬數據
    if _build_with_mock_data(DB_PATH):
        _initialized = True
        return True

    log.error("所有數據源都失敗")
    return False
