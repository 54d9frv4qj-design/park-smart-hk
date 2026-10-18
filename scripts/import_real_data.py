# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 真實數據導入器
從本地歷史快照（運輸署 vacancy_all.json）導入真實停車場數據
數據來源：C:\\Users\\Administrator\\Downloads\\data
"""
import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sqlalchemy import text

# 確保項目根目錄在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import HK_DISTRICTS
from src.db.connection import get_engine, init_db
from src.utils.logger import log

# 18 區中心座標（用於缺少座標時嘅預設值）
DISTRICT_CENTERS = {
    "中西區": (22.2855, 114.1610),
    "灣仔區": (22.2783, 114.1747),
    "東區": (22.2840, 114.2230),
    "南區": (22.2470, 114.1650),
    "油尖旺區": (22.3120, 114.1710),
    "深水埗區": (22.3300, 114.1620),
    "九龍城區": (22.3270, 114.1900),
    "黃大仙區": (22.3420, 114.1970),
    "觀塘區": (22.3130, 114.2250),
    "葵青區": (22.3570, 114.1310),
    "荃灣區": (22.3710, 114.1150),
    "屯門區": (22.3910, 113.9770),
    "元朗區": (22.4450, 114.0330),
    "北區": (22.4950, 114.1380),
    "大埔區": (22.4510, 114.1680),
    "沙田區": (22.3830, 114.1890),
    "西貢區": (22.3810, 114.2700),
    "離島區": (22.2590, 113.9460),
}

# ============================================================
# 配置
# ============================================================
REAL_DATA_DIR = Path(r"C:\Users\Administrator\Downloads\data\https%3A%2F%2Fresource.data.one.gov.hk%2Ftd%2Fcarpark%2F")
BASIC_INFO_CACHE = PROJECT_ROOT / "data" / "basic_info_cache.json"

# 地區英文名 → 繁體中文名映射
DISTRICT_MAP = {
    "Central and Western": "中西區",
    "Central & Western": "中西區",
    "Central&Western": "中西區",
    "Eastern": "東區",
    "Islands": "離島區",
    "Kowloon City": "九龍城區",
    "Kwai Tsing": "葵青區",
    "Kwun Tong": "觀塘區",
    "North": "北區",
    "Sai Kung": "西貢區",
    "Sha Tin": "沙田區",
    "Sham Shui Po": "深水埗區",
    "Southern": "南區",
    "Tai Po": "大埔區",
    "Tsuen Wan": "荃灣區",
    "Tuen Mun": "屯門區",
    "Wan Chai": "灣仔區",
    "Wong Tai Sin": "黃大仙區",
    "Yau Tsim Mong": "油尖旺區",
    "Yuen Long": "元朗區",
}


# ============================================================
# 1. 獲取停車場基本資料
# ============================================================
def fetch_basic_info() -> dict:
    """
    從政府 API 獲取停車場基本資料，以 TD park_Id 為 key
    優先讀取快取，避免重複呼叫 API
    """
    if BASIC_INFO_CACHE.exists():
        log.info(f"從快取載入基本資料: {BASIC_INFO_CACHE}")
        with open(BASIC_INFO_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)

    log.info("從政府 API 獲取停車場基本資料...")
    import requests
    url = "https://api.data.gov.hk/v1/carpark-info-vacancy?data=basic"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    basic = {}
    for item in data.get("results", []):
        park_id = item.get("park_Id", "")
        # 只保留 TD 格式（tdcXXXpY）
        if not park_id.startswith("tdc"):
            continue

        # 解析收費（從 heightLimits remark 中提取時租）
        hourly_fee = None
        daily_fee = None
        night_fee = None
        for hl in item.get("heightLimits", []):
            remark = hl.get("remark", "")
            # 提取時租：$XX/Hour
            m = re.search(r'\$(\d+(?:\.\d+)?)\s*/\s*Hour', remark, re.IGNORECASE)
            if m:
                hourly_fee = float(m.group(1))
            # 提取日泊：Day Park.*?\$(\d+)
            m = re.search(r'Day\s*Park[^$]*\$(\d+(?:\.\d+)?)', remark, re.IGNORECASE)
            if m:
                daily_fee = float(m.group(1))
            # 提取夜泊：Night Park.*?\$(\d+)
            m = re.search(r'Night\s*Park[^$]*\$(\d+(?:\.\d+)?)', remark, re.IGNORECASE)
            if m:
                night_fee = float(m.group(1))

        district_en = item.get("district", "")
        district_zh = DISTRICT_MAP.get(district_en, district_en)

        basic[park_id] = {
            "park_id": park_id,
            "name": item.get("name", park_id),
            "name_en": item.get("name", park_id),
            "district": district_zh,
            "address": item.get("displayAddress", ""),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "contact_phone": item.get("contactNo", ""),
            "hourly_fee": hourly_fee,
            "daily_fee": daily_fee,
            "night_fee": night_fee,
            "opening_hours": "24小時",
            "is_government": 0,
            "has_ev_charging": 1 if "evCharger" in str(item.get("facilities", [])) else 0,
            "has_covered": 1,
            "operator": "運輸署",
        }

    log.info(f"獲取到 {len(basic)} 個 TD 停車場基本資料")

    # 保存快取
    BASIC_INFO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASIC_INFO_CACHE, "w", encoding="utf-8") as f:
        json.dump(basic, f, ensure_ascii=False, indent=2)

    return basic


# ============================================================
# 2. 解析單個 vacancy JSON 檔案
# ============================================================
def parse_vacancy_file(filepath: Path) -> list:
    """
    解析單個 vacancy_all.json 檔案
    返回 list of dict: {park_id, vacancy, vacancy_ev, snapshot_time}
    """
    # 從檔名解析時間：20260901-0030-vacancy_all.json
    fname = filepath.stem
    m = re.match(r'(\d{8})-(\d{4})', fname)
    if not m:
        return []
    date_str, time_str = m.group(1), m.group(2)
    snapshot_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:00"

    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        log.warning(f"讀取失敗 {filepath.name}: {e}")
        return []

    records = []
    for cp in data.get("car_park", []):
        park_id = cp.get("park_id", "")
        if not park_id:
            continue

        vacancy_p = None  # 私家車
        vacancy_m = None  # 電單車
        vacancy_ev = None  # EV

        for vt in cp.get("vehicle_type", []):
            vtype = vt.get("type", "")
            for sc in vt.get("service_category", []):
                vac = sc.get("vacancy")
                if vac is None:
                    continue
                if vtype == "P":
                    vacancy_p = int(vac)
                elif vtype == "M":
                    vacancy_m = int(vac)
                elif vtype == "P_D":
                    # 殘疾人士車位，暫時忽略
                    pass

        if vacancy_p is not None:
            records.append({
                "park_id": park_id,
                "snapshot_time": snapshot_time,
                "vacancy": vacancy_p,
                "vacancy_motorcycle": vacancy_m if vacancy_m is not None else 0,
                "vacancy_ev": vacancy_ev if vacancy_ev is not None else 0,
            })

    return records


# ============================================================
# 3. 批量導入
# ============================================================
def import_real_data(
    data_dir: Path = REAL_DATA_DIR,
    max_files: int = None,
    batch_size: int = 5000,
) -> dict:
    """
    導入真實數據到資料庫

    Args:
        data_dir: 數據目錄
        max_files: 最多處理檔案數（None=全部）
        batch_size: 批量插入大小

    Returns:
        統計信息
    """
    engine = get_engine()
    init_db(engine)

    # 1. 獲取基本資料
    basic_info = fetch_basic_info()

    # 2. 列出所有 vacancy 檔案
    json_files = sorted(data_dir.glob("*vacancy_all.json"))
    if max_files:
        json_files = json_files[:max_files]
    log.info(f"找到 {len(json_files)} 個 vacancy 快照檔案")

    # 3. 先收集所有停車場 ID，計算總車位（用歷史最大空位）
    log.info("第一遍：收集停車場 ID 同最大空位...")
    park_max_vacancy = {}
    park_ids = set()
    for i, fpath in enumerate(json_files):
        records = parse_vacancy_file(fpath)
        for r in records:
            pid = r["park_id"]
            park_ids.add(pid)
            park_max_vacancy[pid] = max(park_max_vacancy.get(pid, 0), r["vacancy"])
        if (i + 1) % 500 == 0:
            log.info(f"  已處理 {i+1}/{len(json_files)} 檔案，發現 {len(park_ids)} 個停車場")

    log.info(f"共發現 {len(park_ids)} 個停車場")

    # 4. 寫入停車場基本資料
    log.info("寫入停車場基本資料...")
    static_records = []
    for pid in sorted(park_ids):
        info = basic_info.get(pid, {})
        # 總車位 = 歷史最大空位 × 1.3（假設滿座時比最大觀察值多 30%）
        total_spaces = int(park_max_vacancy.get(pid, 0) * 1.3)
        if total_spaces == 0:
            total_spaces = 50  # 預設值

        # 如果基本資料冇地區，用座標判斷，或預設
        district = info.get("district", "")
        if not district:
            district = "觀塘區"  # 預設（最多停車場嘅區）

        static_records.append({
            "park_id": pid,
            "name": info.get("name", f"停車場 {pid}"),
            "name_en": info.get("name_en", pid),
            "district": district,
            "address": info.get("address", ""),
            "lat": info.get("lat") or DISTRICT_CENTERS.get(district, (22.32, 114.17))[0],
            "lng": info.get("lng") or DISTRICT_CENTERS.get(district, (22.32, 114.17))[1],
            "total_spaces": total_spaces,
            "ev_spaces": 0,
            "motorcycle_spaces": 0,
            "goods_vehicle_spaces": 0,
            "is_government": info.get("is_government", 0),
            "has_ev_charging": info.get("has_ev_charging", 0),
            "has_covered": info.get("has_covered", 1),
            "hourly_fee": info.get("hourly_fee"),
            "daily_fee": info.get("daily_fee"),
            "monthly_fee": None,
            "night_fee": info.get("night_fee"),
            "fee_estimated": 0 if info.get("hourly_fee") else 1,
            "operator": info.get("operator", "運輸署"),
            "contact_phone": info.get("contact_phone", ""),
            "opening_hours": info.get("opening_hours", "24小時"),
        })

    with engine.connect() as conn:
        for rec in static_records:
            conn.execute(text("""
                INSERT OR REPLACE INTO carparks_static
                    (park_id, name, name_en, district, address, lat, lng,
                     total_spaces, ev_spaces, motorcycle_spaces, goods_vehicle_spaces,
                     is_government, has_ev_charging, has_covered,
                     hourly_fee, daily_fee, monthly_fee, night_fee, fee_estimated,
                     operator, contact_phone, opening_hours)
                VALUES
                    (:park_id, :name, :name_en, :district, :address, :lat, :lng,
                     :total_spaces, :ev_spaces, :motorcycle_spaces, :goods_vehicle_spaces,
                     :is_government, :has_ev_charging, :has_covered,
                     :hourly_fee, :daily_fee, :monthly_fee, :night_fee, :fee_estimated,
                     :operator, :contact_phone, :opening_hours)
            """), rec)
        conn.commit()
    log.info(f"已寫入 {len(static_records)} 個停車場基本資料")

    # 5. 第二遍：導入實時空位數據
    log.info("第二遍：導入實時空位數據...")
    total_records = 0
    batch = []
    start_time = time.time()

    for i, fpath in enumerate(json_files):
        records = parse_vacancy_file(fpath)
        for r in records:
            # 計算佔用率同狀態
            total = park_max_vacancy.get(r["park_id"], 0) * 1.3
            total = max(total, 1)
            occupancy = 1 - (r["vacancy"] / total)
            occupancy = max(0, min(1, occupancy))
            if r["vacancy"] == 0:
                status = "full"
            elif occupancy > 0.9:
                status = "red"
            elif occupancy > 0.7:
                status = "yellow"
            else:
                status = "green"

            batch.append({
                "park_id": r["park_id"],
                "snapshot_time": r["snapshot_time"],
                "vacancy": r["vacancy"],
                "vacancy_ev": r["vacancy_ev"],
                "vacancy_motorcycle": r["vacancy_motorcycle"],
                "occupancy_rate": round(occupancy, 4),
                "status": status,
                "data_source": "api",
            })

        if len(batch) >= batch_size:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT OR IGNORE INTO carparks_realtime
                        (park_id, snapshot_time, vacancy, vacancy_ev, vacancy_motorcycle,
                         occupancy_rate, status, data_source)
                    VALUES
                        (:park_id, :snapshot_time, :vacancy, :vacancy_ev, :vacancy_motorcycle,
                         :occupancy_rate, :status, :data_source)
                """), batch)
                conn.commit()
            total_records += len(batch)
            batch = []

        if (i + 1) % 500 == 0:
            elapsed = time.time() - start_time
            rate = total_records / elapsed if elapsed > 0 else 0
            log.info(f"  已處理 {i+1}/{len(json_files)} 檔案，"
                     f"導入 {total_records:,} 條記錄，速率 {rate:,.0f} 條/秒")

    # 插入剩餘
    if batch:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT OR IGNORE INTO carparks_realtime
                    (park_id, snapshot_time, vacancy, vacancy_ev, vacancy_motorcycle,
                     occupancy_rate, status, data_source)
                VALUES
                    (:park_id, :snapshot_time, :vacancy, :vacancy_ev, :vacancy_motorcycle,
                     :occupancy_rate, :status, :data_source)
            """), batch)
            conn.commit()
        total_records += len(batch)

    elapsed = time.time() - start_time
    log.info(f"✅ 導入完成！共 {total_records:,} 條實時記錄，耗時 {elapsed:.1f} 秒")

    return {
        "carparks": len(park_ids),
        "realtime_records": total_records,
        "files_processed": len(json_files),
        "date_range": f"{json_files[0].stem[:8]} ~ {json_files[-1].stem[:8]}",
    }


# ============================================================
# 主程式
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="泊得好 — 真實數據導入器")
    parser.add_argument("--max-files", type=int, default=None,
                        help="最多處理檔案數（預設全部）")
    parser.add_argument("--data-dir", type=str, default=str(REAL_DATA_DIR),
                        help="數據目錄")
    args = parser.parse_args()

    result = import_real_data(
        data_dir=Path(args.data_dir),
        max_files=args.max_files,
    )
    print("\n" + "=" * 50)
    print("導入統計：")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("=" * 50)
