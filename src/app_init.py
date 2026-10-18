# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — App 啟動初始化
優先使用真實數據（本地歷史快照），唔可用時降級模擬數據
Streamlit Cloud 上 /tmp/ 係臨時檔案系統，每次重新部署都要重建 DB
"""
import os
from pathlib import Path
from sqlalchemy import text

from src.config import STREAMLIT_CLOUD, DB_PATH
from src.db.connection import get_engine, init_db
from src.utils.logger import log

# 真實數據目錄（本地先有，Streamlit Cloud 冇）
REAL_DATA_DIR = Path(os.getenv(
    "REAL_DATA_DIR",
    r"C:\Users\Administrator\Downloads\data\https%3A%2F%2Fresource.data.one.gov.hk%2Ftd%2Fcarpark%2F"
))


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


def has_real_data() -> bool:
    """檢查真實數據目錄是否存在並有 JSON 檔案"""
    if not REAL_DATA_DIR.exists():
        return False
    json_files = list(REAL_DATA_DIR.glob("*vacancy_all.json"))
    return len(json_files) > 10


def ensure_app_ready(force: bool = False) -> bool:
    """
    確保 App 就緒：DB 存在 + 有數據

    優先級：
    1. 本地有真實數據 → 導入真實停車場數據 + 模擬咪錶/天氣
    2. 冇真實數據 → 全部用模擬數據
    3. Streamlit Cloud → 用模擬數據（真實數據檔案唔喺度）

    Args:
        force: 強制重新初始化

    Returns:
        True 如果就緒
    """
    engine = get_engine()

    if force or not is_db_initialized(engine):
        log.info("初始化資料庫...")

        if force and DB_PATH.exists():
            try:
                DB_PATH.unlink()
                log.info(f"已刪除舊 DB: {DB_PATH}")
            except Exception as e:
                log.warning(f"刪除舊 DB 失敗: {e}")

        init_db(engine)
        log.info("Schema 初始化完成")

        use_real = has_real_data() and not STREAMLIT_CLOUD

        if use_real:
            log.info("📡 使用真實數據（運輸署歷史快照）...")
            try:
                from scripts.import_real_data import import_real_data
                result = import_real_data(data_dir=REAL_DATA_DIR)
                log.info(f"真實數據導入完成: {result['carparks']} 停車場, "
                         f"{result['realtime_records']:,} 條記錄")
            except Exception as e:
                log.error(f"真實數據導入失敗，降級模擬數據: {e}")
                use_real = False

        if not use_real:
            log.info("🎲 使用模擬數據生成器...")
            try:
                from src.mock_data.carpark_generator import generate_mock_carparks
                generate_mock_carparks(engine, count=607, days=30)
                log.info("模擬停車場數據生成完成（607 場，30 天）")
            except Exception as e:
                log.error(f"模擬停車場數據生成失敗: {e}")
                return False

        # 咪錶同天氣：永遠用模擬（冇真實數據源）
        try:
            from src.mock_data.meter_generator import generate_mock_meters
            from src.mock_data.weather_generator import generate_mock_weather
            from src.etl.spatial_join import build_carpark_meter_nearby

            log.info("生成模擬咪錶數據（200 組）...")
            generate_mock_meters(engine, count=200, days=30)

            log.info("生成模擬天氣數據...")
            generate_mock_weather(engine, days=30)

            log.info("建立停車場×咪錶空間匹配...")
            build_carpark_meter_nearby(engine, radius_km=2.0)

            log.info("✅ 附加數據生成完成")
        except Exception as e:
            log.warning(f"附加數據生成失敗（唔影響主要功能）: {e}")

    return True


# 模組載入時自動檢查（Streamlit Cloud 首次運行會觸發）
if STREAMLIT_CLOUD:
    ensure_app_ready()
