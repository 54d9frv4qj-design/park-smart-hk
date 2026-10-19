# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 停車場 API 抓取
對接香港政府數據一站通 carpark-info-vacancy API
含完整錯誤處理與模擬數據降級
"""
import time
from typing import List, Dict, Optional

import requests

from src.config import (
    CARPARK_BASIC_URL, CARPARK_VACANCY_URL,
    API_TIMEOUT, API_RATE_LIMIT_SECONDS, API_HEADERS,
)
from src.utils.logger import log


def fetch_basic_info() -> List[Dict]:
    """
    抓取停車場基本資料
    API: https://api.data.gov.hk/v1/carpark-info-vacancy?data=basic
    返回：停車場基本資料列表
    """
    log.info(f"📡 抓取停車場基本資料：{CARPARK_BASIC_URL}")
    try:
        resp = requests.get(
            CARPARK_BASIC_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        # 解析政府 API 結構
        # 實際結構可能是 {"results": [...]} 或直接列表
        results = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            results = [results]

        log.info(f"✅ 取得 {len(results)} 個停車場基本資料")
        return results

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            log.warning("⚠️ API 返回 403，將使用模擬數據")
        else:
            log.error(f"❌ HTTP 錯誤：{e}")
        return []
    except Exception as e:
        log.error(f"❌ 抓取失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def fetch_realtime_vacancy() -> List[Dict]:
    """
    抓取停車場實時空位
    API: https://api.data.gov.hk/v1/carpark-info-vacancy?data=vacancy&vehicleTypes=privateCar&lang=zh_TW
    返回：實時空位記錄列表，每筆含 park_Id, space, spaceEV 等
    """
    log.info(f"📡 抓取停車場實時空位：{CARPARK_VACANCY_URL}")
    try:
        resp = requests.get(
            CARPARK_VACANCY_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            results = [results]

        log.info(f"✅ 取得 {len(results)} 筆實時空位")
        return results

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            log.warning("⚠️ API 返回 403，將使用模擬數據降級")
        else:
            log.error(f"❌ HTTP 錯誤：{e}")
        return []
    except Exception as e:
        log.error(f"❌ 抓取失敗：{e}")
        return []
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def parse_basic_info(raw: Dict) -> Optional[Dict]:
    """
    解析政府 API 基本資料為內部格式
    政府 API 欄位：park_Id, name, nameEN, district, address, lat, lng,
                  vehicleTypes（含 space, spaceEV 等）, parkingCharges
    """
    try:
        park_id = str(raw.get("park_Id", raw.get("park_id", "")))
        if not park_id:
            return None

        vehicle_types = raw.get("vehicleTypes", {})
        private_car = vehicle_types.get("privateCar", {}) if isinstance(vehicle_types, dict) else {}
        charges = raw.get("parkingCharges", {})

        return {
            "park_id": park_id,
            "name": raw.get("name", ""),
            "name_en": raw.get("nameEN", ""),
            "district": raw.get("district", ""),
            "address": raw.get("address", ""),
            "lat": float(raw.get("lat", 0)),
            "lng": float(raw.get("lng", 0)),
            "total_spaces": int(private_car.get("space", 0)),
            "ev_spaces": int(private_car.get("spaceEV", 0)),
            "hourly_fee": charges.get("hourly") if charges else None,
            "daily_fee": charges.get("daily") if charges else None,
            "monthly_fee": charges.get("monthly") if charges else None,
        }
    except Exception as e:
        log.warning(f"解析基本資料失敗：{e}")
        return None


def parse_vacancy(raw: Dict) -> Optional[Dict]:
    """
    解析政府 API 實時空位為內部格式
    關鍵欄位：park_Id, vehicleTypes.privateCar.space（空位）, spaceEV
    """
    try:
        park_id = str(raw.get("park_Id", raw.get("park_id", "")))
        if not park_id:
            return None

        vehicle_types = raw.get("vehicleTypes", {})
        private_car = vehicle_types.get("privateCar", {}) if isinstance(vehicle_types, dict) else {}

        # 政府 API 用 -1 表示滿座/數據暫停，統一轉成 0
        def safe_int(v):
            n = int(v) if v is not None else 0
            return max(0, n)

        return {
            "park_id": park_id,
            "vacancy": safe_int(private_car.get("space", 0)),
            "vacancy_ev": safe_int(private_car.get("spaceEV", 0)),
            "snapshot_time": raw.get("updateTime", ""),
        }
    except Exception as e:
        log.warning(f"解析實時空位失敗：{e}")
        return None
