# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 路邊咪錶模擬數據生成器
生成 200 個咪錶組 + 實時佔用 + 同街道空間插值
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import HK_DISTRICTS, MOCK_METER_COUNT, MOCK_HISTORY_DAYS, MOCK_INTERVAL_MINUTES
from src.utils.haversine import vacancy_status, haversine_m

random.seed(123)

# 香港常見街道名稱（按區）
STREETS_BY_DISTRICT = {
    "中西區": ["德輔道中", "皇后大道中", "畢打街", "威靈頓街", "蘇杭街", "西營盤正街"],
    "灣仔區": ["軒尼詩道", "駱克道", "菲林明道", "灣仔道", "莊士敦道", "太原街"],
    "東區": ["英皇道", "筲箕灣道", "柴灣道", "西灣河街", "北角道", "渣華道"],
    "南區": ["香港仔大道", "黃竹坑道", "赤柱村道", "薄扶林道", "鴨脷洲橋道"],
    "油尖旺區": ["彌敦道", "廣東道", "海防道", "北京道", "旺角道", "西洋菜南街", "花園街", "女人街"],
    "深水埗區": ["長沙灣道", "欽州街", "鴨寮街", "福華街", "北河街", "大南街"],
    "九龍城區": ["太子道西", "賈炳達道", "城南道", "東正道", "九龍城道"],
    "黃大仙區": ["龍翔道", "大成街", "雙鳳街", "正德街", "彩虹道"],
    "觀塘區": ["觀塘道", "牛頭角道", "裕民坊", "協和街", "開源道", "偉業街"],
    "葵青區": ["葵涌道", "興芳路", "葵富路", "青衣鄉事會路", "長青路"],
    "荃灣區": ["荃灣街市街", "大河道", "沙咀道", "楊屋道", "青山公路荃灣段"],
    "屯門區": ["屯門鄉事會路", "屯利街", "杯渡路", "青雲路", "建生街"],
    "元朗區": ["元朗安樂路", "青山公路元朗段", "大馬路", "豐年路", "元朗體育路"],
    "北區": ["上水石湖墟路", "粉嶺聯和墟路", "沙頭角公路", "馬會道"],
    "大埔區": ["大埔太和路", "大埔墟站路", "南盛街", "寶鄉街", "廣福道"],
    "沙田區": ["沙田正街", "沙田鄉事會路", "大埔公路沙田段", "火炭路", "小瀝源路"],
    "西貢區": ["西貢市中心", "將軍澳唐明街", "坑口常寧路", "調景嶺景嶺路"],
    "離島區": ["東涌達東路", "長洲大新街", "坪洲永安街", "梅窩碼頭路"],
}


def _generate_meter_static(meter_id: str, district: dict) -> Dict:
    """生成單個咪錶組基本資料"""
    streets = STREETS_BY_DISTRICT.get(district["name"], ["正街"])
    street = random.choice(streets)

    # 經緯度：區中心附近
    lat = district["lat"] + random.uniform(-0.015, 0.015)
    lng = district["lng"] + random.uniform(-0.015, 0.015)

    # 咪錶數量：2-8 個
    num_meters = random.randint(2, 8)
    total_spaces = num_meters * random.randint(1, 2)  # 每咪錶 1-2 位

    # 收費：港島/九龍較貴，新界較平
    hourly = round(4 + district["density"] * 12 + random.uniform(-2, 2), 0)
    hourly = max(4, min(16, hourly))

    return {
        "meter_id": meter_id,
        "group_name": f"{street}咪錶組",
        "street_name": street,
        "district": district["name"],
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "total_meters": num_meters,
        "total_spaces": total_spaces,
        "hourly_fee": hourly,
        "max_duration": random.choice([60, 120, 120, 180, 240]),
        "payment_methods": ",".join(random.sample(
            ["八達通", "信用卡", "手機支付", "現金"], random.randint(2, 4)
        )),
        "is_new_meter": random.choice([1, 1, 1, 0]),
        "operating_hours": "08:00-22:00" if random.random() > 0.2 else "09:00-19:00",
    }


def _meter_occupancy_pattern(dt: datetime, district_density: float) -> float:
    """咪錶佔用率模式（比停車場波動更大）"""
    hour = dt.hour
    weekday = dt.weekday()

    # 咪錶夜間不營運，佔用率低
    if hour < 8 or hour >= 22:
        return random.uniform(0.05, 0.2)

    base = 0.35 + 0.25 * math.sin((hour - 8) / 14 * math.pi)

    if weekday < 5:
        if 12 <= hour < 14:
            base += 0.2
        if 17 <= hour < 19:
            base += 0.15
    else:
        if 10 <= hour < 18:
            base += 0.2

    base += district_density * 0.15
    base += random.gauss(0, 0.1)  # 咪錶波動更大

    return max(0.0, min(1.0, base))


def generate_mock_meters(engine: Engine, count: int = None, days: int = None) -> None:
    """生成模擬咪錶數據並寫入 DB"""
    count = count or MOCK_METER_COUNT
    days = days or MOCK_HISTORY_DAYS

    print(f"[Mock] 生成 {count} 個咪錶組 + {days} 天歷史數據...")

    # 按地區分配
    total_density = sum(d["density"] for d in HK_DISTRICTS)
    meters = []
    meter_id_counter = 1
    remaining = count

    for i, d in enumerate(HK_DISTRICTS):
        if i == len(HK_DISTRICTS) - 1:
            alloc = remaining
        else:
            alloc = max(3, int(count * d["density"] / total_density))
            remaining -= alloc
        for _ in range(alloc):
            m = _generate_meter_static(f"M{meter_id_counter:04d}", d)
            meters.append(m)
            meter_id_counter += 1

    # 寫入靜態資料
    with engine.connect() as conn:
        for m in meters:
            conn.execute(text(
                """
                INSERT OR REPLACE INTO metered_parking
                    (meter_id, group_name, street_name, district, lat, lng,
                     total_meters, total_spaces, hourly_fee, max_duration,
                     payment_methods, is_new_meter, operating_hours)
                VALUES
                    (:meter_id, :group_name, :street_name, :district, :lat, :lng,
                     :total_meters, :total_spaces, :hourly_fee, :max_duration,
                     :payment_methods, :is_new_meter, :operating_hours)
                """
            ), m)
        conn.commit()

    print(f"[Mock] 咪錶靜態資料寫入完成：{len(meters)} 組")

    # 生成歷史佔用數據
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    intervals = []
    current = start_time
    while current <= end_time:
        intervals.append(current)
        current += timedelta(minutes=MOCK_INTERVAL_MINUTES)

    district_density_map = {d["name"]: d["density"] for d in HK_DISTRICTS}
    batch = []
    batch_size = 1000

    for m in meters:
        density = district_density_map.get(m["district"], 0.5)
        for dt in intervals:
            occ = _meter_occupancy_pattern(dt, density)
            occupied = min(m["total_spaces"], int(m["total_spaces"] * occ + random.gauss(0, 0.5)))
            vacant = m["total_spaces"] - occupied
            status, occ_rate = vacancy_status(vacant, m["total_spaces"])

            # 模擬部分咪錶數據缺失（用空間插值標記）
            is_interpolated = 1 if random.random() < 0.05 else 0

            batch.append({
                "meter_id": m["meter_id"],
                "snapshot_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "vacant_spaces": vacant,
                "occupied_spaces": occupied,
                "occupancy_rate": occ_rate,
                "status": status,
                "is_interpolated": is_interpolated,
                "data_source": "mock",
            })

            if len(batch) >= batch_size:
                with engine.connect() as conn:
                    conn.execute(text(
                        """
                        INSERT INTO meter_occupancy
                            (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                             occupancy_rate, status, is_interpolated, data_source)
                        VALUES
                            (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                             :occupancy_rate, :status, :is_interpolated, :data_source)
                        """
                    ), batch)
                    conn.commit()
                batch = []

    if batch:
        with engine.connect() as conn:
            conn.execute(text(
                """
                INSERT INTO meter_occupancy
                    (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                     occupancy_rate, status, is_interpolated, data_source)
                VALUES
                    (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                     :occupancy_rate, :status, :is_interpolated, :data_source)
                """
            ), batch)
            conn.commit()

    print(f"[Mock] 咪錶歷史數據寫入完成：約 {len(intervals) * len(meters):,} 筆")


def spatial_interpolate_meters(meters: List[Dict], radius_m: float = 200) -> List[Dict]:
    """
    同街道空間插值：若某咪錶數據缺失，用方圓 radius_m 內相鄰咪錶的均值估算
    """
    result = []
    for i, m in enumerate(meters):
        if m.get("vacant_spaces") is not None:
            result.append(m)
            continue
        # 找相鄰咪錶
        neighbors = []
        for j, other in enumerate(meters):
            if i == j:
                continue
            dist = haversine_m(m["lat"], m["lng"], other["lat"], other["lng"])
            if dist <= radius_m and other.get("vacant_spaces") is not None:
                neighbors.append(other)
        if neighbors:
            avg_vacant = sum(n["vacant_spaces"] for n in neighbors) / len(neighbors)
            avg_occupied = sum(n["occupied_spaces"] for n in neighbors) / len(neighbors)
            m["vacant_spaces"] = int(avg_vacant)
            m["occupied_spaces"] = int(avg_occupied)
            m["is_interpolated"] = 1
        result.append(m)
    return result
