# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — ETL 管線
抓取 → 清洗 → 正則化 → 空間匹配 → 寫入 DB
API 失敗時自動降級為模擬數據
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from sqlalchemy.engine import Engine

from src.config import DATABASE_URL
from src.db.connection import get_engine, init_db
from src.db.queries import (
    upsert_realtime_vacancy, upsert_meter_occupancy, upsert_weather,
    determine_status,
)
from src.data_fetch.carpark_api import fetch_basic_info, fetch_realtime_vacancy, parse_vacancy
from src.data_fetch.meter_api import fetch_meter_distribution, fetch_meter_occupancy
from src.data_fetch.weather_api import fetch_current_weather, fetch_weather_warnings
from src.mock_data.carpark_generator import generate_mock_realtime_snapshot
from src.etl.cleaners import clean_carpark_data, clean_meter_data, clean_weather_data
from src.etl.spatial_join import build_carpark_meter_nearby
from src.utils.logger import log
from src.utils.haversine import now_hkt, format_hkt


def run_etl(engine: Engine = None, use_mock: bool = False) -> Dict:
    """
    執行完整 ETL 管線
    :param engine: 資料庫 Engine（None 則自動建立）
    :param use_mock: 是否強制使用模擬數據
    :return: 統計資訊 dict
    """
    if engine is None:
        engine = get_engine()
        init_db(engine)

    stats = {
        "carparks_fetched": 0,
        "carparks_written": 0,
        "meters_fetched": 0,
        "meters_written": 0,
        "weather_fetched": False,
        "used_mock": False,
        "errors": [],
        "start_time": format_hkt(now_hkt()),
    }

    # ============================================================
    # 1. 停車場實時空位
    # ============================================================
    log.info("=" * 50)
    log.info("🚗 開始 ETL：停車場實時空位")
    log.info("=" * 50)

    vacancy_records = []
    if not use_mock:
        raw_vacancy = fetch_realtime_vacancy()
        if raw_vacancy:
            for raw in raw_vacancy:
                parsed = parse_vacancy(raw)
                if parsed:
                    vacancy_records.append(parsed)
            stats["carparks_fetched"] = len(vacancy_records)
        else:
            log.warning("⚠️ API 無數據，降級為模擬數據")
            use_mock = True

    if use_mock or not vacancy_records:
        log.info("🎲 使用模擬數據生成實時快照")
        vacancy_records = generate_mock_realtime_snapshot()
        stats["used_mock"] = True
        stats["carparks_fetched"] = len(vacancy_records)

    # 清洗並寫入
    now_str = format_hkt(now_hkt())
    for rec in vacancy_records:
        try:
            cleaned = clean_carpark_data(rec)
            cleaned["snapshot_time"] = cleaned.get("snapshot_time") or now_str
            cleaned["data_source"] = "mock" if stats["used_mock"] else "api"
            upsert_realtime_vacancy(engine, cleaned)
            stats["carparks_written"] += 1
        except Exception as e:
            stats["errors"].append(f"carpark {rec.get('park_id', '?')}: {e}")

    log.info(f"✅ 停車場：抓取 {stats['carparks_fetched']}，寫入 {stats['carparks_written']}")

    # ============================================================
    # 2. 咪錶實時佔用
    # ============================================================
    log.info("=" * 50)
    log.info("⏱️ 開始 ETL：咪錶實時佔用")
    log.info("=" * 50)

    if not use_mock:
        raw_meters = fetch_meter_occupancy()
        if raw_meters:
            meter_records = [clean_meter_data(r) for r in raw_meters if r]
            stats["meters_fetched"] = len(meter_records)
            for rec in meter_records:
                try:
                    rec["snapshot_time"] = rec.get("snapshot_time") or now_str
                    rec["data_source"] = "api"
                    upsert_meter_occupancy(engine, rec)
                    stats["meters_written"] += 1
                except Exception as e:
                    stats["errors"].append(f"meter: {e}")
        else:
            log.info("ℹ️ 咪錶 API 無數據，跳過（咪錶靜態資料已在初始化時寫入）")
    else:
        log.info("ℹ️ 模擬模式：咪錶數據已在初始化時生成")

    # ============================================================
    # 3. 天氣
    # ============================================================
    log.info("=" * 50)
    log.info("🌤️ 開始 ETL：天氣數據")
    log.info("=" * 50)

    if not use_mock:
        weather = fetch_current_weather()
        if weather:
            warnings = fetch_weather_warnings()
            weather.update(warnings)
            cleaned = clean_weather_data(weather)
            cleaned["snapshot_time"] = cleaned.get("snapshot_time") or now_str
            try:
                upsert_weather(engine, cleaned)
                stats["weather_fetched"] = True
                log.info(f"✅ 天氣：{cleaned.get('weather_desc', '?')}")
            except Exception as e:
                stats["errors"].append(f"weather: {e}")
    else:
        log.info("ℹ️ 模擬模式：天氣數據已在初始化時生成")

    # ============================================================
    # 4. 空間匹配（停車場×咪錶）
    # ============================================================
    log.info("=" * 50)
    log.info("📍 開始 ETL：停車場×咪錶空間匹配")
    log.info("=" * 50)
    try:
        nearby_count = build_carpark_meter_nearby(engine, radius_km=0.5)
        log.info(f"✅ 空間匹配完成：{nearby_count} 對關聯")
    except Exception as e:
        stats["errors"].append(f"spatial_join: {e}")
        log.warning(f"⚠️ 空間匹配跳過：{e}")

    stats["end_time"] = format_hkt(now_hkt())
    log.info("=" * 50)
    log.info(f"🎉 ETL 完成｜停車場 {stats['carparks_written']}｜咪錶 {stats['meters_written']}｜"
             f"天氣 {'✓' if stats['weather_fetched'] else '✗'}｜"
             f"模擬 {'是' if stats['used_mock'] else '否'}")
    if stats["errors"]:
        log.warning(f"⚠️ {len(stats['errors'])} 個錯誤")
    log.info("=" * 50)

    return stats


if __name__ == "__main__":
    use_mock = "--mock" in sys.argv
    run_etl(use_mock=use_mock)
