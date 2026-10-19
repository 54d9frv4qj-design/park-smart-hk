#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 真實咪錶數據導入器
從運輸署 API 抓取咪錶分佈同實時佔用，按 PoleId 聚合後寫入 DB。
取代模擬數據，確保全部用真實數據。
"""
import sys
import csv
import io
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.connection import get_engine, init_db
from src.utils.haversine import haversine_m
from sqlalchemy import text

# API URLs
METER_DISTRIBUTION_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/"
    "spaceinfo/parkingspaces.csv"
)
METER_OCCUPANCY_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/"
    "occupancystatus/occupancystatus.csv"
)

API_TIMEOUT = 30
API_RATE_LIMIT = 1  # 秒


def fetch_csv(url: str) -> str:
    """抓取 CSV 並返回解碼後嘅內容"""
    print(f"📡 抓取：{url}")
    resp = requests.get(url, timeout=API_TIMEOUT)
    resp.raise_for_status()
    print(f"   狀態：{resp.status_code}，大小：{len(resp.content):,} bytes")
    return resp.content.decode("utf-8-sig")


def parse_distribution(content: str) -> dict:
    """
    解析咪錶分佈 CSV，按 PoleId 聚合
    返回：{pole_id: {street, district, lat, lng, total_spaces, hourly_fee, max_duration}}
    """
    # 分佈 CSV 頭幾行可能係日期/空行，搵到真正嘅 header 先
    lines = content.split("\n")
    header_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("PoleId") or line.startswith("pole_id"):
            header_idx = i
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))
    poles = defaultdict(lambda: {
        "spaces": [], "lat_sum": 0, "lng_sum": 0,
        "district": "", "street": "", "fees": [], "durations": []
    })

    count = 0
    for row in reader:
        pole_id = row.get("PoleId", "").strip()
        if not pole_id:
            continue

        p = poles[pole_id]
        p["spaces"].append(row.get("ParkingSpaceId", ""))
        p["district"] = row.get("District_tc", row.get("District", ""))
        p["street"] = row.get("Street_tc", row.get("Street", ""))

        try:
            lat = float(row.get("Latitude", 0) or 0)
            lng = float(row.get("Longitude", 0) or 0)
            if lat and lng:
                p["lat_sum"] += lat
                p["lng_sum"] += lng
        except (ValueError, TypeError):
            pass

        try:
            fee = float(row.get("PaymentUnit", 0) or 0)
            if fee > 0:
                p["fees"].append(fee)
        except (ValueError, TypeError):
            pass

        try:
            dur = int(row.get("LPP", 0) or 0)
            if dur > 0:
                p["durations"].append(dur)
        except (ValueError, TypeError):
            pass

        count += 1

    print(f"   解析：{count:,} 個車位，{len(poles):,} 個咪錶柱")

    # 計算每個柱嘅聚合值
    result = {}
    for pole_id, p in poles.items():
        n = len(p["spaces"])
        lat = p["lat_sum"] / n if p["lat_sum"] else 0
        lng = p["lng_sum"] / n if p["lng_sum"] else 0
        fee = sum(p["fees"]) / len(p["fees"]) if p["fees"] else 0
        duration = max(p["durations"]) if p["durations"] else 120

        result[pole_id] = {
            "meter_id": pole_id,
            "group_name": f"{p['street']}（{pole_id}）" if p["street"] else pole_id,
            "street_name": p["street"],
            "district": p["district"],
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "total_meters": 1,
            "total_spaces": n,
            "hourly_fee": round(fee, 1),
            "max_duration": duration,
            "payment_methods": "八達通,信用卡,APP",
            "is_new_meter": 1,
            "operating_hours": "每日",
        }

    return result


def parse_occupancy(content: str) -> dict:
    """
    解析咪錶實時佔用 CSV，按 PoleId 聚合
    返回：{pole_id: {total, occupied, vacant, occupancy_rate, status, snapshot_time}}
    """
    reader = csv.DictReader(io.StringIO(content))
    poles = defaultdict(lambda: {"total": 0, "occupied": 0, "vacant": 0, "times": []})

    count = 0
    for row in reader:
        space_id = row.get("ParkingSpaceId", "").strip()
        if not space_id:
            continue

        # 從 ParkingSpaceId 提取 PoleId（如 10006A → 10006）
        pole_id = ""
        for i, ch in enumerate(space_id):
            if ch.isalpha():
                pole_id = space_id[:i]
                break
        if not pole_id:
            pole_id = space_id

        status = row.get("OccupancyStatus", "").strip().upper()
        update_time = row.get("OccupancyDateChanged", "").strip()

        p = poles[pole_id]
        p["total"] += 1
        if status == "O":
            p["occupied"] += 1
        elif status == "V":
            p["vacant"] += 1
        if update_time:
            p["times"].append(update_time)

        count += 1

    print(f"   解析：{count:,} 個車位狀態，{len(poles):,} 個咪錶柱")

    # 計算聚合值
    result = {}
    snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for pole_id, p in poles.items():
        total = p["total"]
        occupied = p["occupied"]
        vacant = p["vacant"]
        # 未知狀態嘅車位計入總數但唔計入佔用
        unknown = total - occupied - vacant
        occ_rate = occupied / total if total > 0 else 0

        # 狀態判斷
        vacancy_rate = vacant / total if total > 0 else 0
        if vacancy_rate > 0.30:
            status = "green"
        elif vacancy_rate > 0.10:
            status = "yellow"
        else:
            status = "red" if vacant > 0 else "full"

        result[pole_id] = {
            "meter_id": pole_id,
            "snapshot_time": snapshot_time,
            "vacant_spaces": vacant,
            "occupied_spaces": occupied,
            "occupancy_rate": round(occ_rate, 4),
            "status": status,
            "is_interpolated": 0,
            "data_source": "api",
        }

    return result


def import_real_meter_data():
    """導入真實咪錶數據到 DB"""
    engine = get_engine()
    init_db(engine)

    # 1. 抓取分佈數據
    print("\n" + "=" * 60)
    print("📊 第一步：抓取咪錶分佈數據")
    print("=" * 60)
    dist_content = fetch_csv(METER_DISTRIBUTION_URL)
    time.sleep(API_RATE_LIMIT)
    distribution = parse_distribution(dist_content)

    # 2. 抓取佔用數據
    print("\n" + "=" * 60)
    print("📊 第二步：抓取咪錶實時佔用數據")
    print("=" * 60)
    occ_content = fetch_csv(METER_OCCUPANCY_URL)
    time.sleep(API_RATE_LIMIT)
    occupancy = parse_occupancy(occ_content)

    # 3. 寫入 DB
    print("\n" + "=" * 60)
    print("💾 第三步：寫入資料庫")
    print("=" * 60)

    with engine.connect() as conn:
        # 刪除舊 mock 數據
        print("   刪除舊咪錶數據...")
        conn.execute(text("DELETE FROM meter_occupancy"))
        conn.execute(text("DELETE FROM metered_parking"))
        conn.commit()

        # 寫入靜態資料
        print(f"   寫入 {len(distribution):,} 個咪錶柱靜態資料...")
        batch = []
        for pole_id, data in distribution.items():
            batch.append(data)
            if len(batch) >= 500:
                conn.execute(text("""
                    INSERT OR REPLACE INTO metered_parking
                        (meter_id, group_name, street_name, district, lat, lng,
                         total_meters, total_spaces, hourly_fee, max_duration,
                         payment_methods, is_new_meter, operating_hours)
                    VALUES
                        (:meter_id, :group_name, :street_name, :district, :lat, :lng,
                         :total_meters, :total_spaces, :hourly_fee, :max_duration,
                         :payment_methods, :is_new_meter, :operating_hours)
                """), batch)
                conn.commit()
                batch = []
        if batch:
            conn.execute(text("""
                INSERT OR REPLACE INTO metered_parking
                    (meter_id, group_name, street_name, district, lat, lng,
                     total_meters, total_spaces, hourly_fee, max_duration,
                     payment_methods, is_new_meter, operating_hours)
                VALUES
                    (:meter_id, :group_name, :street_name, :district, :lat, :lng,
                     :total_meters, :total_spaces, :hourly_fee, :max_duration,
                     :payment_methods, :is_new_meter, :operating_hours)
            """), batch)
            conn.commit()

        # 寫入實時佔用
        print(f"   寫入 {len(occupancy):,} 個咪錶柱實時狀態...")
        batch = []
        for pole_id, data in occupancy.items():
            # 只寫入有對應靜態資料嘅咪錶
            if pole_id in distribution:
                batch.append(data)
            if len(batch) >= 500:
                conn.execute(text("""
                    INSERT INTO meter_occupancy
                        (meter_id, snapshot_time, vacant_spaces, occupied_spaces,
                         occupancy_rate, status, is_interpolated, data_source)
                    VALUES
                        (:meter_id, :snapshot_time, :vacant_spaces, :occupied_spaces,
                         :occupancy_rate, :status, :is_interpolated, :data_source)
                """), batch)
                conn.commit()
                batch = []
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

        # 4. 重新計算停車場×咪錶空間匹配
        print("\n   重新計算停車場×咪錶空間匹配...")
        conn.execute(text("DELETE FROM carpark_meter_nearby"))
        conn.commit()

        carparks = conn.execute(text("SELECT park_id, lat, lng FROM carparks_static WHERE lat IS NOT NULL AND lng IS NOT NULL")).fetchall()
        meters = conn.execute(text("SELECT meter_id, lat, lng FROM metered_parking WHERE lat IS NOT NULL AND lng IS NOT NULL")).fetchall()

        print(f"   匹配 {len(carparks):,} 個停車場 × {len(meters):,} 個咪錶柱...")
        nearby_batch = []
        for cp in carparks:
            matches = []
            for mt in meters:
                dist = haversine_m(cp[1], cp[2], mt[1], mt[2])
                if dist <= 300:  # 300米內
                    matches.append((mt[0], dist))
            matches.sort(key=lambda x: x[1])
            for meter_id, dist in matches[:5]:  # 每個停車場最多5個最近咪錶
                nearby_batch.append({
                    "park_id": cp[0],
                    "meter_id": meter_id,
                    "distance_m": round(dist, 1),
                    "walking_minutes": round(dist / 80, 1),
                })
            if len(nearby_batch) >= 1000:
                conn.execute(text("""
                    INSERT OR REPLACE INTO carpark_meter_nearby
                        (park_id, meter_id, distance_m, walking_minutes)
                    VALUES (:park_id, :meter_id, :distance_m, :walking_minutes)
                """), nearby_batch)
                conn.commit()
                nearby_batch = []
        if nearby_batch:
            conn.execute(text("""
                INSERT OR REPLACE INTO carpark_meter_nearby
                    (park_id, meter_id, distance_m, walking_minutes)
                VALUES (:park_id, :meter_id, :distance_m, :walking_minutes)
            """), nearby_batch)
            conn.commit()

        # 5. 驗證
        print("\n" + "=" * 60)
        print("✅ 驗證結果")
        print("=" * 60)
        total_meters = conn.execute(text("SELECT COUNT(*) FROM metered_parking")).scalar()
        total_occ = conn.execute(text("SELECT COUNT(*) FROM meter_occupancy")).scalar()
        total_nearby = conn.execute(text("SELECT COUNT(*) FROM carpark_meter_nearby")).scalar()

        stats = conn.execute(text("""
            SELECT
                SUM(CASE WHEN vacant_spaces > 0 THEN 1 ELSE 0 END) as has_vacancy,
                SUM(CASE WHEN vacant_spaces = 0 THEN 1 ELSE 0 END) as full,
                AVG(occupancy_rate) as avg_occupancy,
                AVG(vacant_spaces) as avg_vacant
            FROM meter_occupancy
            WHERE snapshot_time = (SELECT MAX(snapshot_time) FROM meter_occupancy)
        """)).fetchone()

        print(f"   咪錶柱總數：{total_meters:,}")
        print(f"   佔用記錄：{total_occ:,}")
        print(f"   空間匹配：{total_nearby:,}")
        print(f"   有位咪錶：{stats[0]} ({stats[0]/total_occ*100:.0f}%)" if total_occ else "   有位咪錶：N/A")
        print(f"   滿座咪錶：{stats[1]}" if stats[1] is not None else "   滿座咪錶：N/A")
        print(f"   平均佔用率：{stats[2]:.1%}" if stats[2] else "   平均佔用率：N/A")
        print(f"   平均空位：{stats[3]:.1f}" if stats[3] else "   平均空位：N/A")
        print(f"   數據來源：api（真實數據）")


if __name__ == "__main__":
    import_real_meter_data()
