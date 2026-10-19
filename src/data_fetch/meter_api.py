# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 路邊咪錶 API 抓取
對接運輸署咪錶分佈 CSV + 新咪錶實時佔用 API
真實數據來源：https://resource.data.one.gov.hk/td/psiparkingspaces/
"""
import csv
import io
import time
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

import requests

from src.config import (
    METER_DISTRIBUTION_URL, METER_OCCUPANCY_URL,
    CSDI_METER_URL, CSDI_TOKEN,
    API_TIMEOUT, API_RATE_LIMIT_SECONDS, API_HEADERS,
)
from src.utils.logger import log


def fetch_meter_distribution() -> List[Dict]:
    """
    抓取全港咪錶泊車位分佈 CSV（真實數據）
    返回：咪錶位置資料列表（按 PoleId 聚合）
    """
    log.info(f"📡 抓取咪錶分佈 CSV：{METER_DISTRIBUTION_URL}")
    try:
        resp = requests.get(
            METER_DISTRIBUTION_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()

        content = resp.content.decode("utf-8-sig")
        # 分佈 CSV 頭幾行可能係日期/空行，搵到真正嘅 header 先
        lines = content.split("\n")
        header_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("PoleId") or line.startswith("pole_id"):
                header_idx = i
                break
        reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))

        # 按 PoleId 聚合（一個咪錶柱有多個車位）
        poles = defaultdict(lambda: {
            "spaces": [], "lat_sum": 0, "lng_sum": 0,
            "district": "", "street": "", "fees": [], "durations": []
        })

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

        # 轉換為內部格式
        results = []
        for pole_id, p in poles.items():
            n = len(p["spaces"])
            results.append({
                "meter_id": pole_id,
                "group_name": f"{p['street']}（{pole_id}）" if p["street"] else pole_id,
                "street_name": p["street"] or "未命名街道",
                "district": p["district"] or "未知",
                "lat": round(p["lat_sum"] / n, 6) if p["lat_sum"] else 0,
                "lng": round(p["lng_sum"] / n, 6) if p["lng_sum"] else 0,
                "total_meters": 1,
                "total_spaces": n,
                "hourly_fee": round(sum(p["fees"]) / len(p["fees"]), 1) if p["fees"] else 0,
                "max_duration": max(p["durations"]) if p["durations"] else 120,
                "payment_methods": "八達通,信用卡,APP",
                "is_new_meter": 1,
                "operating_hours": "每日",
            })

        log.info(f"✅ 取得 {len(results)} 個咪錶柱（{sum(r['total_spaces'] for r in results):,} 個車位）")
        return results

    except Exception as e:
        log.error(f"❌ 抓取咪錶分佈失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def fetch_meter_occupancy() -> List[Dict]:
    """
    抓取新咪錶實時佔用狀態 CSV（真實數據）
    按 PoleId 聚合，返回內部格式：meter_id, vacant_spaces, occupied_spaces, occupancy_rate, status
    """
    log.info(f"📡 抓取咪錶實時佔用：{METER_OCCUPANCY_URL}")
    try:
        resp = requests.get(
            METER_OCCUPANCY_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()

        content = resp.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        # 按 PoleId 聚合（從 ParkingSpaceId 如 10006A 提取 10006）
        poles = defaultdict(lambda: {"total": 0, "occupied": 0, "vacant": 0})

        for row in reader:
            space_id = row.get("ParkingSpaceId", "").strip()
            if not space_id:
                continue
            # 提取字母前嘅數字部分作為 PoleId
            pole_id = ""
            for i, ch in enumerate(space_id):
                if ch.isalpha():
                    pole_id = space_id[:i]
                    break
            if not pole_id:
                pole_id = space_id

            status = row.get("OccupancyStatus", "").strip().upper()
            p = poles[pole_id]
            p["total"] += 1
            if status == "O":
                p["occupied"] += 1
            elif status == "V":
                p["vacant"] += 1

        # 轉換為內部格式
        snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = []
        for pole_id, p in poles.items():
            total = p["total"]
            occupied = p["occupied"]
            vacant = p["vacant"]
            occ_rate = occupied / total if total > 0 else 0
            vacancy_rate = vacant / total if total > 0 else 0

            if vacancy_rate > 0.30:
                status = "green"
            elif vacancy_rate > 0.10:
                status = "yellow"
            else:
                status = "red" if vacant > 0 else "full"

            results.append({
                "meter_id": pole_id,
                "snapshot_time": snapshot_time,
                "vacant_spaces": vacant,
                "occupied_spaces": occupied,
                "occupancy_rate": round(occ_rate, 4),
                "status": status,
                "is_interpolated": 0,
                "data_source": "api",
            })

        log.info(f"✅ 取得 {len(results)} 個咪錶柱實時狀態")
        return results

    except Exception as e:
        log.error(f"❌ 抓取咪錶實時狀態失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def fetch_meter_csdi() -> List[Dict]:
    """
    從 CSDI 抓取咪錶地理數據（ArcGIS FeatureServer）
    注意：CSDI 可能返回 403 或 499 Token Required
    """
    if not CSDI_TOKEN:
        log.info("ℹ️ 未配置 CSDI_TOKEN，跳過 CSDI 抓取")
        return []

    log.info(f"📡 從 CSDI 抓取咪錶數據...")
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "outSR": "4326",
        "token": CSDI_TOKEN,
    }
    try:
        resp = requests.get(
            CSDI_METER_URL,
            params=params,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            log.warning(f"⚠️ CSDI 錯誤：{data['error']}")
            return []

        features = data.get("features", [])
        results = [f.get("attributes", {}) for f in features]
        log.info(f"✅ CSDI 取得 {len(results)} 筆咪錶資料")
        return results

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in [403, 499]:
            log.warning(f"⚠️ CSDI 返回 {e.response.status_code}，需要 Token 或調整 Headers")
        else:
            log.error(f"❌ CSDI HTTP 錯誤：{e}")
        return []
    except Exception as e:
        log.error(f"❌ CSDI 抓取失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def parse_meter_distribution(raw: Dict) -> Dict:
    """解析咪錶分佈 CSV 行為內部格式"""
    return {
        "meter_id": str(raw.get("MeterID", raw.get("meter_id", ""))),
        "street_name": raw.get("StreetName", raw.get("street", "")),
        "district": raw.get("District", raw.get("district", "")),
        "lat": float(raw.get("Latitude", raw.get("lat", 0)) or 0),
        "lng": float(raw.get("Longitude", raw.get("lng", 0)) or 0),
        "total_spaces": int(raw.get("NumberOfSpaces", raw.get("spaces", 0)) or 0),
        "hourly_fee": float(raw.get("HourlyCharge", raw.get("fee", 0)) or 0),
        "max_duration": int(raw.get("MaxParkingMinutes", raw.get("max_minutes", 120)) or 120),
    }


def parse_meter_occupancy(raw: Dict) -> Dict:
    """解析咪錶實時佔用 CSV 行為內部格式"""
    status = raw.get("Status", raw.get("status", "")).upper()
    return {
        "meter_id": str(raw.get("MeterID", raw.get("meter_id", ""))),
        "status_raw": status,
        "is_vacant": status == "V",
        "snapshot_time": raw.get("UpdateTime", raw.get("update_time", "")),
    }
