# -*- coding: utf-8 -*-
"""
重新生成更真實嘅咪錶佔用數據
高峰時段高佔用、部分滿座，夜間低佔用
"""
import sys
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.connection import get_engine
from sqlalchemy import text

random.seed(42)

def realistic_occupancy(dt: datetime, district_density: float) -> float:
    """更真實嘅咪錶佔用率模式"""
    hour = dt.hour
    weekday = dt.weekday()

    # 夜間（0-8）：低佔用，但唔會零
    if hour < 8:
        return random.uniform(0.1, 0.35)

    # 深夜（22-24）
    if hour >= 22:
        return random.uniform(0.15, 0.4)

    # 日間基線
    base = 0.45

    # 早上高峰（8-10）
    if 8 <= hour < 10:
        base = 0.75
    # 上午（10-12）
    elif 10 <= hour < 12:
        base = 0.55
    # 午飯高峰（12-14）— 最繁忙
    elif 12 <= hour < 14:
        base = 0.85
    # 下午（14-17）
    elif 14 <= hour < 17:
        base = 0.6
    # 放工高峰（17-19）
    elif 17 <= hour < 19:
        base = 0.8
    # 傍晚（19-22）
    elif 19 <= hour < 22:
        base = 0.45

    # 工作日 vs 週末
    if weekday >= 5:  # 週末
        if 10 <= hour < 18:
            base += 0.1  # 週末日間更繁忙
        else:
            base -= 0.1  # 週末早晚較少人

    # 地區密度調整
    base += (district_density - 0.5) * 0.2

    # 隨機波動
    base += random.gauss(0, 0.08)

    return max(0.05, min(0.99, base))


def regenerate_meter_data():
    engine = get_engine()

    with engine.connect() as conn:
        # 取得所有咪錶
        meters = conn.execute(text("""
            SELECT meter_id, district, total_spaces FROM metered_parking
        """)).fetchall()
        print(f"取得 {len(meters)} 個咪錶組")

        # 地區密度
        district_density = {
            "油尖旺區": 0.95, "觀塘區": 0.85, "灣仔區": 0.9, "中西區": 0.88,
            "九龍城區": 0.75, "深水埗區": 0.7, "東區": 0.65, "南區": 0.5,
            "黃大仙區": 0.6, "葵青區": 0.6, "荃灣區": 0.65, "屯門區": 0.55,
            "元朗區": 0.5, "北區": 0.45, "大埔區": 0.5, "沙田區": 0.7,
            "西貢區": 0.45, "離島區": 0.35,
        }

        # 刪除舊數據
        conn.execute(text("DELETE FROM meter_occupancy"))
        conn.commit()
        print("已刪除舊數據")

        # 生成 14 天數據，每 15 分鐘
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)
        intervals = []
        current = start_time
        while current <= end_time:
            intervals.append(current)
            current += timedelta(minutes=15)

        print(f"生成 {len(intervals)} 個時間點 × {len(meters)} 個咪錶 = {len(intervals)*len(meters):,} 筆")

        batch = []
        batch_size = 2000
        total = 0

        for m in meters:
            meter_id, district, total_spaces = m
            density = district_density.get(district, 0.6)

            for dt in intervals:
                occ = realistic_occupancy(dt, density)
                occupied = min(total_spaces, max(0, int(total_spaces * occ + random.gauss(0, 0.3))))
                vacant = total_spaces - occupied

                # 計算狀態
                vacancy_rate = vacant / total_spaces if total_spaces > 0 else 0
                if vacancy_rate > 0.30:
                    status = "green"
                elif vacancy_rate > 0.10:
                    status = "yellow"
                else:
                    status = "red" if vacant > 0 else "full"

                occupancy_rate = round(1 - vacancy_rate, 4)

                batch.append({
                    "meter_id": meter_id,
                    "snapshot_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "vacant_spaces": vacant,
                    "occupied_spaces": occupied,
                    "occupancy_rate": occupancy_rate,
                    "status": status,
                    "is_interpolated": 0,
                    "data_source": "mock",
                })

                if len(batch) >= batch_size:
                    conn.execute(text("""
                        INSERT INTO meter_occupancy
                            (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                             occupancy_rate, status, is_interpolated, data_source)
                        VALUES
                            (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                             :occupancy_rate, :status, :is_interpolated, :data_source)
                    """), batch)
                    conn.commit()
                    total += len(batch)
                    batch = []
                    if total % 50000 == 0:
                        print(f"  已寫入 {total:,} 筆")

        if batch:
            conn.execute(text("""
                INSERT INTO meter_occupancy
                    (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                     occupancy_rate, status, is_interpolated, data_source)
                VALUES
                    (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                     :occupancy_rate, :status, :is_interpolated, :data_source)
            """), batch)
            conn.commit()
            total += len(batch)

        print(f"✅ 完成：共 {total:,} 筆")

        # 驗證最新數據
        stats = conn.execute(text("""
            SELECT
                COUNT(*) as total_meters,
                SUM(CASE WHEN o.vacant_spaces > 0 THEN 1 ELSE 0 END) as has_vacancy,
                AVG(o.occupancy_rate) as avg_occupancy,
                AVG(o.vacant_spaces) as avg_vacant
            FROM metered_parking m
            LEFT JOIN (
                SELECT meter_id, MAX(snapshot_time) as max_t
                FROM meter_occupancy GROUP BY meter_id
            ) latest ON m.meter_id = latest.meter_id
            LEFT JOIN meter_occupancy o ON m.meter_id = o.meter_id AND o.snapshot_time = latest.max_t
        """)).fetchone()
        print(f"\n最新數據統計：")
        print(f"  總咪錶: {stats[0]}")
        print(f"  有位: {stats[1]} ({stats[1]/stats[0]*100:.0f}%)")
        print(f"  平均佔用率: {stats[2]:.1%}")
        print(f"  平均空位: {stats[3]:.1f}")


if __name__ == "__main__":
    regenerate_meter_data()
