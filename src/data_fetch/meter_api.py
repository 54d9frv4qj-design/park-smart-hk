# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 路邊咪錶 API 抓取
對接運輸署咪錶分佈 CSV + 新咪錶實時佔用 API
含 CSDI 403 處理與模擬數據降級
"""
import csv
import io
import time
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
    抓取全港咪錶泊車位分佈 CSV
    返回：咪錶位置資料列表
    """
    log.info(f"📡 抓取咪錶分佈 CSV：{METER_DISTRIBUTION_URL}")
    try:
        resp = requests.get(
            METER_DISTRIBUTION_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()

        # 解析 CSV
        content = resp.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        results = list(reader)

        log.info(f"✅ 取得 {len(results)} 筆咪錶分佈資料")
        return results

    except Exception as e:
        log.error(f"❌ 抓取咪錶分佈失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def fetch_meter_occupancy() -> List[Dict]:
    """
    抓取新咪錶實時佔用狀態 CSV
    返回：咪錶實時狀態列表（V=空置, O=佔用）
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
        results = list(reader)

        log.info(f"✅ 取得 {len(results)} 筆咪錶實時狀態")
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
