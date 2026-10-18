# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — App 啟動初始化
Streamlit Cloud 上 /tmp/ 係臨時檔案系統，每次重新部署都要重建 DB
呢個模組負責：檢查 DB → 初始化 Schema → 填入模擬數據
"""
from pathlib import Path
from sqlalchemy import text

from src.config import STREAMLIT_CLOUD, DB_PATH
from src.db.connection import get_engine, init_db
from src.utils.logger import log


def is_db_initialized(engine) -> bool:
    """檢查 DB 是否已初始化（有冇 carparks_static 表同數據）"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='carparks_static'"
            )).fetchone()
            if not result:
                return False
            count = conn.execute(text("SELECT COUNT(*) FROM carparks_static")).scalar()
            return count > 0
    except Exception:
        return False


def ensure_app_ready(force: bool = False) -> bool:
    """
    確保 App 就緒：DB 存在 + 有數據

    Args:
        force: 強制重新初始化（刪除舊 DB）

    Returns:
        True 如果就緒
    """
    engine = get_engine()

    # Streamlit Cloud：每次冷啟動都要重建（/tmp/ 唔會持久化）
    if force or not is_db_initialized(engine):
        log.info("初始化資料庫...")

        # 強制模式：刪除舊 DB
        if force and DB_PATH.exists():
            try:
                DB_PATH.unlink()
                log.info(f"已刪除舊 DB: {DB_PATH}")
            except Exception as e:
                log.warning(f"刪除舊 DB 失敗: {e}")

        # 初始化 Schema
        init_db(engine)
        log.info("Schema 初始化完成")

        # 填入模擬數據
        try:
            from src.mock_data.carpark_generator import generate_mock_carparks
            from src.mock_data.meter_generator import generate_mock_meters
            from src.mock_data.weather_generator import generate_mock_weather
            from src.etl.spatial_join import build_carpark_meter_nearby

            log.info("生成模擬停車場數據（607 場，30 天歷史）...")
            generate_mock_carparks(engine, count=607, days=30)

            log.info("生成模擬咪錶數據（200 組）...")
            generate_mock_meters(engine, count=200, days=30)

            log.info("生成模擬天氣數據...")
            generate_mock_weather(engine, days=30)

            log.info("建立停車場×咪錶空間匹配...")
            build_carpark_meter_nearby(engine, radius_km=2.0)

            log.info("✅ 模擬數據生成完成")
        except Exception as e:
            log.error(f"模擬數據生成失敗: {e}")
            return False

    return True


# 模組載入時自動檢查（Streamlit Cloud 首次運行會觸發）
if STREAMLIT_CLOUD:
    ensure_app_ready()
