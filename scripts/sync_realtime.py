#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 實時數據同步腳本
每小時由 GitHub Actions 呼叫，抓取全港停車場實時空位並寫入 DB；API 失敗就跳過，唔用模擬數據。
"""
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from src.data_fetch.carpark_api import fetch_realtime_vacancy, fetch_basic_info
from src.data_fetch.meter_api import fetch_meter_occupancy
from src.db.connection import get_engine
from src.db.queries import upsert_realtime_vacancy
from sqlalchemy import text

# 日誌設定
logger.add("logs/sync_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", level="INFO")


def sync_carparks(engine) -> tuple[int, int]:
    """同步停車場實時空位，回傳 (成功筆數, 失敗筆數)"""
    success, fail = 0, 0
    try:
        logger.info("📡 抓取停車場基本資料...")
        basic = fetch_basic_info()
        logger.info(f"   取得 {len(basic)} 個停車場基本資料")

        logger.info("📡 抓取停車場實時空位...")
        vacancy = fetch_realtime_vacancy()
        logger.info(f"   取得 {len(vacancy)} 筆實時空位")

        for record in vacancy:
            try:
                upsert_realtime_vacancy(engine, record)
                success += 1
            except Exception as e:
                logger.warning(f"   寫入失敗 {record.get('park_Id', '?')}: {e}")
                fail += 1
    except Exception as e:
        logger.error(f"❌ 停車場 API 抓取失敗：{e}")
        logger.warning("⚠️ 跳過本次停車場同步（唔使用模擬數據）")
    return success, fail


def sync_meters(engine) -> tuple[int, int]:
    """同步咪錶實時佔用（批量插入），回傳 (成功筆數, 失敗筆數)"""
    success, fail = 0, 0
    try:
        logger.info("📡 抓取咪錶實時佔用...")
        occupancy = fetch_meter_occupancy()
        logger.info(f"   取得 {len(occupancy)} 筆咪錶狀態")

        # 批量插入，每 500 筆一次
        batch = []
        for record in occupancy:
            batch.append(record)
            if len(batch) >= 500:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO meter_occupancy
                                (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                                 occupancy_rate, status, is_interpolated, data_source)
                            VALUES
                                (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                                 :occupancy_rate, :status, :is_interpolated, :data_source)
                        """), batch)
                        conn.commit()
                    success += len(batch)
                except Exception as e:
                    logger.warning(f"   咪錶批量寫入失敗：{e}")
                    fail += len(batch)
                batch = []

        if batch:
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO meter_occupancy
                            (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                             occupancy_rate, status, is_interpolated, data_source)
                        VALUES
                            (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                             :occupancy_rate, :status, :is_interpolated, :data_source)
                    """), batch)
                    conn.commit()
                success += len(batch)
            except Exception as e:
                logger.warning(f"   咪錶批量寫入失敗：{e}")
                fail += len(batch)

    except Exception as e:
        logger.error(f"❌ 咪錶 API 抓取失敗：{e}（跳過本次咪錶同步）")
    return success, fail


def main():
    start = time.time()
    logger.info(f"{'='*60}")
    logger.info(f"⏰ 實時同步開始 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    engine = get_engine()

    cp_ok, cp_fail = sync_carparks(engine)
    mt_ok, mt_fail = sync_meters(engine)

    elapsed = time.time() - start
    logger.info(f"{'='*60}")
    logger.info(f"✅ 同步完成｜耗時 {elapsed:.1f}s")
    logger.info(f"   停車場：成功 {cp_ok} / 失敗 {cp_fail}")
    logger.info(f"   咪錶：  成功 {mt_ok} / 失敗 {mt_fail}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
