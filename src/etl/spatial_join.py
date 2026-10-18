# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 空間匹配
停車場×咪錶 Haversine 空間關聯
"""
from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.utils.haversine import haversine_m, walking_minutes
from src.utils.logger import log


def build_carpark_meter_nearby(
    engine: Engine, radius_km: float = 0.5
) -> int:
    """
    建立停車場×咪錶空間匹配表
    為每個停車場找方圓 radius_km 內的咪錶組
    :return: 建立的關聯數量
    """
    # 讀取所有停車場
    with engine.connect() as conn:
        carparks = conn.execute(text(
            "SELECT park_id, lat, lng FROM carparks_static"
        )).mappings().all()
        meters = conn.execute(text(
            "SELECT meter_id, lat, lng FROM metered_parking"
        )).mappings().all()

    if not carparks or not meters:
        log.warning("⚠️ 停車場或咪錶數據不足，跳過空間匹配")
        return 0

    log.info(f"📍 空間匹配：{len(carparks)} 停車場 × {len(meters)} 咪錶，半徑 {radius_km}km")

    # 清空舊匹配
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM carpark_meter_nearby"))
        conn.commit()

    # 建立匹配
    batch = []
    radius_m = radius_km * 1000
    count = 0

    for cp in carparks:
        for mt in meters:
            dist = haversine_m(cp["lat"], cp["lng"], mt["lat"], mt["lng"])
            if dist <= radius_m:
                batch.append({
                    "park_id": cp["park_id"],
                    "meter_id": mt["meter_id"],
                    "distance_m": round(dist, 1),
                    "walking_minutes": walking_minutes(dist),
                })
                count += 1

                if len(batch) >= 500:
                    _write_nearby_batch(engine, batch)
                    batch = []

    if batch:
        _write_nearby_batch(engine, batch)

    log.info(f"✅ 空間匹配完成：{count} 對關聯")
    return count


def _write_nearby_batch(engine: Engine, batch: List[Dict]) -> None:
    """批量寫入空間匹配"""
    with engine.connect() as conn:
        conn.execute(text(
            """
            INSERT OR REPLACE INTO carpark_meter_nearby
                (park_id, meter_id, distance_m, walking_minutes)
            VALUES
                (:park_id, :meter_id, :distance_m, :walking_minutes)
            """
        ), batch)
        conn.commit()


def get_nearby_meters(
    engine: Engine, park_id: str, limit: int = 5
) -> List[Dict]:
    """取得某停車場附近的咪錶組"""
    query = text(
        """
        SELECT n.*, m.street_name, m.district, m.hourly_fee,
               m.total_spaces, o.vacant_spaces, o.occupancy_rate, o.status
        FROM carpark_meter_nearby n
        JOIN metered_parking m ON n.meter_id = m.meter_id
        LEFT JOIN (
            SELECT meter_id, MAX(snapshot_time) as max_t
            FROM meter_occupancy GROUP BY meter_id
        ) latest ON m.meter_id = latest.meter_id
        LEFT JOIN meter_occupancy o
            ON m.meter_id = o.meter_id AND o.snapshot_time = latest.max_t
        WHERE n.park_id = :pid
        ORDER BY n.distance_m ASC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"pid": park_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def get_nearby_carparks_to_meter(
    engine: Engine, meter_id: str, limit: int = 5
) -> List[Dict]:
    """取得某咪錶組附近的停車場"""
    query = text(
        """
        SELECT n.*, s.name, s.district, s.hourly_fee, s.total_spaces,
               r.vacancy, r.occupancy_rate, r.status
        FROM carpark_meter_nearby n
        JOIN carparks_static s ON n.park_id = s.park_id
        LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id
        WHERE n.meter_id = :mid
        ORDER BY n.distance_m ASC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"mid": meter_id, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
