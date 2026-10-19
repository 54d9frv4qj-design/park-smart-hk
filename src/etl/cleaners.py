# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 數據清洗函數
處理缺失值、異常值、格式統一
"""
from typing import Dict, List, Optional
from datetime import datetime

from src.utils.haversine import vacancy_status
from src.utils.timeutil import hkt_now_str


def clean_carpark_data(raw: Dict) -> Dict:
    """
    清洗停車場實時空位數據
    - 統一 park_id 格式
    - 處理缺失值
    - 計算佔用率與狀態
    """
    cleaned = {}

    # park_id：轉字串，去除空白
    cleaned["park_id"] = str(raw.get("park_id", "")).strip()

    # 空位數：確保非負整數
    vacancy = raw.get("vacancy", raw.get("space", 0))
    try:
        cleaned["vacancy"] = max(0, int(float(vacancy)))
    except (ValueError, TypeError):
        cleaned["vacancy"] = 0

    # EV 空位
    vacancy_ev = raw.get("vacancy_ev", raw.get("spaceEV", 0))
    try:
        cleaned["vacancy_ev"] = max(0, int(float(vacancy_ev)))
    except (ValueError, TypeError):
        cleaned["vacancy_ev"] = 0

    # 快照時間
    snapshot_time = raw.get("snapshot_time", raw.get("updateTime", ""))
    if snapshot_time:
        cleaned["snapshot_time"] = _normalize_time(snapshot_time)
    else:
        cleaned["snapshot_time"] = hkt_now_str()

    # 總車位（從 static 表獲取，這裡先預設）
    total_spaces = raw.get("total_spaces", 100)
    try:
        total_spaces = int(total_spaces)
    except (ValueError, TypeError):
        total_spaces = 100

    # 計算佔用率與狀態
    status, occupancy = vacancy_status(cleaned["vacancy"], total_spaces)
    cleaned["occupancy_rate"] = occupancy
    cleaned["status"] = status

    # 數據來源
    cleaned["data_source"] = raw.get("data_source", "api")

    return cleaned


def clean_meter_data(raw: Dict) -> Dict:
    """
    清洗咪錶實時佔用數據
    - 統一狀態（V/O → vacant/occupied）
    - 處理缺失值
    """
    cleaned = {}

    cleaned["meter_id"] = str(raw.get("meter_id", "")).strip()

    # 狀態解析
    status_raw = str(raw.get("status_raw", raw.get("status", ""))).upper()
    is_vacant = raw.get("is_vacant", status_raw == "V")

    total = raw.get("total_spaces", raw.get("total_meters", 1))
    try:
        total = int(total)
    except (ValueError, TypeError):
        total = 1

    if is_vacant:
        cleaned["vacant_spaces"] = total
        cleaned["occupied_spaces"] = 0
    else:
        cleaned["vacant_spaces"] = 0
        cleaned["occupied_spaces"] = total

    # 佔用率
    cleaned["occupancy_rate"] = round(cleaned["occupied_spaces"] / max(total, 1), 4)
    cleaned["status"] = "green" if cleaned["vacant_spaces"] > total * 0.3 else (
        "yellow" if cleaned["vacant_spaces"] > 0 else "red"
    )

    cleaned["is_interpolated"] = int(raw.get("is_interpolated", 0))
    cleaned["data_source"] = raw.get("data_source", "api")
    cleaned["snapshot_time"] = raw.get("snapshot_time", hkt_now_str())

    return cleaned


def clean_weather_data(raw: Dict) -> Dict:
    """
    清洗天氣數據
    - 統一數值範圍
    - 處理缺失值
    """
    cleaned = {}

    # 氣溫：香港合理範圍 0-40°C
    temp = raw.get("temperature")
    try:
        temp = float(temp)
        cleaned["temperature"] = temp if 0 <= temp <= 40 else None
    except (ValueError, TypeError):
        cleaned["temperature"] = None

    # 濕度：0-100%
    humidity = raw.get("humidity")
    try:
        humidity = float(humidity)
        cleaned["humidity"] = humidity if 0 <= humidity <= 100 else None
    except (ValueError, TypeError):
        cleaned["humidity"] = None

    # 雨量：非負
    rainfall = raw.get("rainfall", 0)
    try:
        cleaned["rainfall"] = max(0.0, float(rainfall))
    except (ValueError, TypeError):
        cleaned["rainfall"] = 0.0

    cleaned["weather_desc"] = raw.get("weather_desc", "多雲")
    cleaned["weather_icon"] = raw.get("weather_icon", 3)
    cleaned["has_warning"] = int(raw.get("has_warning", 0))
    cleaned["warning_type"] = raw.get("warning_type", "")
    cleaned["district"] = raw.get("district", "全港")
    cleaned["uv_index"] = raw.get("uv_index", 0)
    cleaned["snapshot_time"] = raw.get("snapshot_time", hkt_now_str())

    return cleaned


def _normalize_time(time_str: str) -> str:
    """統一時間格式為 YYYY-MM-DD HH:MM:SS"""
    if not time_str:
        return hkt_now_str()

    # 嘗試多種格式
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    # 無法解析則返回當前時間
    return hkt_now_str()


def validate_carpark_record(record: Dict) -> bool:
    """驗證停車場記錄是否有效"""
    if not record.get("park_id"):
        return False
    if record.get("vacancy") is None:
        return False
    return True


def remove_duplicates(records: List[Dict], key: str = "park_id") -> List[Dict]:
    """按 key 去除重複記錄（保留最後一條）"""
    seen = {}
    for r in records:
        k = r.get(key)
        if k:
            seen[k] = r
    return list(seen.values())
