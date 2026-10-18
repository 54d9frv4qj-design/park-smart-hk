# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 停車場模擬數據生成器
生成 607 個停車場（18 區分佈）+ 歷史空位時間序列
確保離線可運行，API 失敗時自動降級
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import (
    HK_DISTRICTS, MOCK_CARPARK_COUNT, MOCK_HISTORY_DAYS,
    MOCK_INTERVAL_MINUTES, FEE_RANGES, GOVERNMENT_CARPARTS,
)
from src.utils.haversine import vacancy_status

# 固定隨機種子，確保可重現
random.seed(42)

# 停車場名稱模板（港式）
CARPARK_NAME_PREFIXES = [
    "中環", "灣仔", "銅鑼灣", "尖沙咀", "旺角", "油麻地", "深水埗",
    "九龍塘", "九龍灣", "觀塘", "荃灣", "沙田", "大埔", "元朗",
    "屯門", "將軍澳", "葵芳", "青衣", "香港站", "九龍站",
]
CARPARK_NAME_SUFFIXES = [
    "廣場停車場", "商場停車場", "中心停車場", "大廈停車場",
    "街市停車場", "公園停車場", "體育館停車場", "圖書館停車場",
    "政府停車場", "綜合大樓停車場", "廣場", "商場", "中心",
]
GOVERNMENT_NAMES = [
    "中環天星碼頭停車場", "灣仔峽道停車場", "銅鑼灣停車場",
    "尖沙咀天星碼頭停車場", "旺角花園街停車場", "油麻地停車場",
    "深水埗欽州街停車場", "九龍塘聯合道停車場", "九龍灣偉業街停車場",
    "觀塘碼頭停車場", "荃灣運輸大樓停車場", "沙田大會堂停車場",
    "大埔廣場停車場", "元朗安樂路停車場", "屯門市中心停車場",
    "將軍澳坑口停車場", "葵芳興芳路停車場", "青衣長青停車場",
    "香港仔停車場", "赤柱停車場", "西灣河停車場", "筲箕灣停車場",
    "長沙灣停車場", "牛頭角停車場", "粉嶺停車場", "上水停車場",
]


def _generate_carpark_static(park_id: str, district: dict, idx: int) -> Dict:
    """生成單個停車場基本資料"""
    # 26 個政府場用真實名稱，其餘用組合名
    if idx < GOVERNMENT_CARPARTS:
        name = GOVERNMENT_NAMES[idx % len(GOVERNMENT_NAMES)]
        is_gov = 1
        fee_estimated = 0
    else:
        prefix = random.choice(CARPARK_NAME_PREFIXES)
        suffix = random.choice(CARPARK_NAME_SUFFIXES)
        name = f"{prefix}{suffix}"
        is_gov = 0
        fee_estimated = 1

    # 經緯度：在區中心附近隨機偏移（±0.02度≈2km）
    lat = district["lat"] + random.uniform(-0.02, 0.02)
    lng = district["lng"] + random.uniform(-0.02, 0.02)

    # 車位數：商業區多，住宅區少
    base_spaces = int(80 + district["density"] * 200)
    total_spaces = max(20, int(random.gauss(base_spaces, base_spaces * 0.3)))
    ev_spaces = int(total_spaces * random.uniform(0.02, 0.12))
    motorcycle = int(total_spaces * random.uniform(0.05, 0.15))
    goods = int(total_spaces * random.uniform(0, 0.1))

    # 收費：商業區貴，住宅區平
    density = district["density"]
    hourly = round(FEE_RANGES["hourly"][0] + density * (FEE_RANGES["hourly"][1] - FEE_RANGES["hourly"][0]) * random.uniform(0.7, 1.3), 0)
    hourly = max(FEE_RANGES["hourly"][0], min(FEE_RANGES["hourly"][1], hourly))
    daily = round(hourly * random.uniform(6, 10), 0)
    monthly = round(daily * random.uniform(12, 18), 0)
    night = round(hourly * random.uniform(3, 6), 0)

    return {
        "park_id": park_id,
        "name": name,
        "name_en": f"Carpark {park_id}",
        "district": district["name"],
        "address": f"{district['name']}{random.choice(['民光街', '軒尼詩道', '彌敦道', '廣東道', '青山公路', '沙田正街', '觀塘道'])} {random.randint(1, 200)}號",
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "total_spaces": total_spaces,
        "ev_spaces": ev_spaces,
        "motorcycle_spaces": motorcycle,
        "goods_vehicle_spaces": goods,
        "is_government": is_gov,
        "has_ev_charging": 1 if ev_spaces > 0 else 0,
        "has_covered": random.choice([1, 1, 1, 0]),
        "hourly_fee": hourly,
        "daily_fee": daily,
        "monthly_fee": monthly,
        "night_fee": night,
        "fee_estimated": fee_estimated,
        "operator": random.choice(["領展", "恆基", "新鴻基", "太古", "政府", "其他"]),
        "contact_phone": f"2{random.randint(100, 999)}{random.randint(1000, 9999)}",
        "opening_hours": "24小時" if random.random() > 0.3 else "07:00-23:00",
    }


def _occupancy_pattern(dt: datetime, district_density: float, total_spaces: int) -> float:
    """
    計算某時間點的模擬佔用率
    包含：日夜週期、尖峰、週末差異、隨機波動
    """
    hour = dt.hour
    weekday = dt.weekday()

    # 基礎日夜曲線（正弦波）
    base = 0.4 + 0.3 * math.sin((hour - 6) / 24 * 2 * math.pi)

    # 尖峰加成
    if weekday < 5:  # 週一至五
        if 7 <= hour < 9:      # 早尖峰
            base += 0.25
        elif 12 <= hour < 14:  # 午飯
            base += 0.15
        elif 17 <= hour < 19:  # 晚尖峰
            base += 0.30
    else:  # 週末
        if 11 <= hour < 18:   # 週末下午購物高峰
            base += 0.20
        elif 19 <= hour < 22:  # 週末晚間
            base += 0.10

    # 地區密度加成
    base += district_density * 0.15

    # 深夜降低
    if hour < 6 or hour >= 23:
        base *= 0.4

    # 隨機波動
    base += random.gauss(0, 0.05)

    # 限制在 0.05-0.98
    return max(0.05, min(0.98, base))


def generate_mock_carparks(engine: Engine, count: int = None, days: int = None) -> None:
    """
    生成模擬停車場數據並寫入 DB
    :param count: 停車場數量（預設 607）
    :param days: 歷史天數（預設 30）
    """
    count = count or MOCK_CARPARK_COUNT
    days = days or MOCK_HISTORY_DAYS

    print(f"[Mock] 生成 {count} 個停車場 + {days} 天歷史數據...")

    # 按地區密度分配停車場數量
    total_density = sum(d["density"] for d in HK_DISTRICTS)
    district_allocations = []
    remaining = count
    for i, d in enumerate(HK_DISTRICTS):
        if i == len(HK_DISTRICTS) - 1:
            alloc = remaining
        else:
            alloc = max(5, int(count * d["density"] / total_density))
            remaining -= alloc
        district_allocations.append((d, alloc))

    # 生成靜態資料
    carparks = []
    park_id_counter = 1001
    for district, alloc in district_allocations:
        for i in range(alloc):
            cp = _generate_carpark_static(str(park_id_counter), district, park_id_counter - 1001)
            carparks.append(cp)
            park_id_counter += 1

    # 寫入靜態資料
    with engine.connect() as conn:
        for cp in carparks:
            conn.execute(text(
                """
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
                """
            ), cp)
        conn.commit()

    print(f"[Mock] 靜態資料寫入完成：{len(carparks)} 個停車場")

    # 生成歷史時間序列
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    intervals = []
    current = start_time
    while current <= end_time:
        intervals.append(current)
        current += timedelta(minutes=MOCK_INTERVAL_MINUTES)

    print(f"[Mock] 生成 {len(intervals)} 個時間點 × {len(carparks)} 停車場...")

    # 批量寫入歷史數據（每 1000 筆 commit 一次）
    batch = []
    batch_size = 1000
    district_density_map = {d["name"]: d["density"] for d in HK_DISTRICTS}

    for cp in carparks:
        density = district_density_map.get(cp["district"], 0.5)
        for dt in intervals:
            occ = _occupancy_pattern(dt, density, cp["total_spaces"])
            vacancy = max(0, int(cp["total_spaces"] * (1 - occ) + random.gauss(0, 2)))
            vacancy = min(vacancy, cp["total_spaces"])
            status, occ_rate = vacancy_status(vacancy, cp["total_spaces"])

            batch.append({
                "park_id": cp["park_id"],
                "snapshot_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "vacancy": vacancy,
                "vacancy_ev": max(0, int(cp["ev_spaces"] * (1 - occ) * random.uniform(0.8, 1.2))),
                "occupancy_rate": occ_rate,
                "status": status,
                "data_source": "mock",
            })

            if len(batch) >= batch_size:
                with engine.connect() as conn:
                    conn.execute(text(
                        """
                        INSERT INTO carparks_realtime
                            (park_id, snapshot_time, vacancy, vacancy_ev,
                             occupancy_rate, status, data_source)
                        VALUES
                            (:park_id, :snapshot_time, :vacancy, :vacancy_ev,
                             :occupancy_rate, :status, :data_source)
                        """
                    ), batch)
                    conn.commit()
                batch = []

    # 寫入剩餘
    if batch:
        with engine.connect() as conn:
            conn.execute(text(
                """
                INSERT INTO carparks_realtime
                    (park_id, snapshot_time, vacancy, vacancy_ev,
                     occupancy_rate, status, data_source)
                VALUES
                    (:park_id, :snapshot_time, :vacancy, :vacancy_ev,
                     :occupancy_rate, :status, :data_source)
                """
            ), batch)
            conn.commit()

    total_records = len(intervals) * len(carparks)
    print(f"[Mock] 歷史數據寫入完成：約 {total_records:,} 筆記錄")


def generate_mock_realtime_snapshot() -> List[Dict]:
    """
    生成一次模擬實時快照（用於 ETL 降級）
    返回實時空位記錄列表
    """
    # 從 DB 讀取停車場列表
    from src.db.connection import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT park_id, total_spaces, district FROM carparks_static"
        )).mappings().all()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    district_density_map = {d["name"]: d["density"] for d in HK_DISTRICTS}

    results = []
    for row in rows:
        density = district_density_map.get(row["district"], 0.5)
        occ = _occupancy_pattern(datetime.now(), density, row["total_spaces"])
        vacancy = max(0, int(row["total_spaces"] * (1 - occ) + random.gauss(0, 2)))
        vacancy = min(vacancy, row["total_spaces"])
        status, occ_rate = vacancy_status(vacancy, row["total_spaces"])
        results.append({
            "park_id": row["park_id"],
            "snapshot_time": now,
            "vacancy": vacancy,
            "vacancy_ev": max(0, int(row["total_spaces"] * 0.05 * (1 - occ))),
            "occupancy_rate": occ_rate,
            "status": status,
            "data_source": "mock",
        })
    return results
