# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 更新停車場中文名稱
從政府 API 獲取 zh_TW 中文名，更新 carparks_static 表
"""
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.connection import get_engine
from src.utils.logger import log

BASIC_URL = "https://api.data.gov.hk/v1/carpark-info-vacancy?data=basic"


def fetch_basic_info(lang: str = None) -> dict:
    """從政府 API 取得停車場基本資料"""
    url = BASIC_URL
    if lang:
        url += f"&lang={lang}"
    log.info(f"取得基本資料 (lang={lang or 'default'})...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", data) if isinstance(data, dict) else data
    log.info(f"  取得 {len(results)} 個停車場")
    return {item["park_Id"]: item for item in results}


def update_chinese_names():
    """更新停車場中文名稱"""
    engine = get_engine()

    # 取得中英文基本資料
    basic_en = fetch_basic_info()
    time.sleep(1)
    basic_zh = fetch_basic_info("zh_TW")

    updated = 0
    with engine.connect() as conn:
        # 取得所有停車場 ID
        park_ids = [row[0] for row in conn.execute(
            text("SELECT park_id FROM carparks_static")
        ).fetchall()]
        log.info(f"數據庫有 {len(park_ids)} 個停車場")

        for pid in park_ids:
            zh = basic_zh.get(pid)
            en = basic_en.get(pid)

            if zh:
                name_zh = zh.get("name", "")
                district_zh = zh.get("district", "")
                address_zh = zh.get("displayAddress", "")
            else:
                name_zh = ""
                district_zh = ""
                address_zh = ""

            if en:
                name_en = en.get("name", pid)
            else:
                name_en = pid

            # 如果有中文名，用中文名；否則用英文名
            final_name = name_zh if name_zh else name_en

            conn.execute(text("""
                UPDATE carparks_static
                SET name = :name,
                    name_en = :name_en,
                    district = COALESCE(NULLIF(:district, ''), district),
                    address = COALESCE(NULLIF(:address, ''), address)
                WHERE park_id = :pid
            """), {
                "name": final_name,
                "name_en": name_en,
                "district": district_zh,
                "address": address_zh,
                "pid": pid,
            })
            updated += 1

            if updated % 100 == 0:
                log.info(f"  已更新 {updated}/{len(park_ids)}")

        conn.commit()

    # 統計
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM carparks_static")).scalar()
        chinese = conn.execute(text("""
            SELECT COUNT(*) FROM carparks_static
            WHERE name GLOB '*[一-鿿]*'
        """)).scalar()
    log.info(f"✅ 更新完成: {updated} 個停車場，其中 {chinese}/{total} 有中文名")


if __name__ == "__main__":
    update_chinese_names()
