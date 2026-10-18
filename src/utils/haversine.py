# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 工具函數
"""
import math
from datetime import datetime, timedelta
from typing import Tuple

# ============================================================
# Haversine 球面距離
# ============================================================
def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """計算兩點之間的球面距離（公里）"""
    R = 6371.0  # 地球半徑（km）
    lat1_r, lng1_r = math.radians(lat1), math.radians(lng1)
    lat2_r, lng2_r = math.radians(lat2), math.radians(lng2)
    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """計算兩點之間的球面距離（米）"""
    return haversine_km(lat1, lng1, lat2, lng2) * 1000


def walking_minutes(distance_m: float, speed_m_per_min: float = 80.0) -> float:
    """步行時間估算（分鐘），預設速度 80m/min"""
    return round(distance_m / speed_m_per_min, 1)


# ============================================================
# 時間工具
# ============================================================
HKT_OFFSET = timedelta(hours=8)


def now_hkt() -> datetime:
    """取得當前香港時間（UTC+8）"""
    return datetime.utcnow() + HKT_OFFSET


def format_hkt(dt: datetime) -> str:
    """格式化為香港時間字串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_weekend(dt: datetime) -> bool:
    """判斷是否週末（週六=5, 週日=6）"""
    return dt.weekday() >= 5


def is_peak_hour(dt: datetime) -> str:
    """
    判斷尖峰時段
    返回：'morning_peak' / 'evening_peak' / 'lunch' / 'off_peak'
    """
    h = dt.hour
    wd = dt.weekday()
    if wd < 5:  # 週一至五
        if 7 <= h < 9:
            return "morning_peak"
        elif 12 <= h < 14:
            return "lunch"
        elif 17 <= h < 19:
            return "evening_peak"
    return "off_peak"


def get_time_period(hour: int) -> str:
    """取得時段名稱"""
    if 6 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "午飯"
    elif 14 <= hour < 18:
        return "下午"
    elif 18 <= hour < 22:
        return "晚間"
    else:
        return "深夜"


def generate_time_intervals(
    start: datetime, end: datetime, interval_minutes: int = 15
) -> list:
    """生成時間區間列表"""
    intervals = []
    current = start
    while current < end:
        intervals.append(current)
        current += timedelta(minutes=interval_minutes)
    return intervals


# ============================================================
# 狀態判斷
# ============================================================
def vacancy_status(vacancy: int, total: int) -> Tuple[str, float]:
    """
    根據空位數與總數判斷狀態
    返回：(status, occupancy_rate)
    """
    if total <= 0 or vacancy is None:
        return "unknown", 0.0
    occupancy = max(0.0, min(1.0, 1 - (vacancy / total)))
    vacancy_rate = 1 - occupancy
    if vacancy_rate > 0.30:
        status = "green"
    elif vacancy_rate > 0.10:
        status = "yellow"
    else:
        status = "red" if vacancy > 0 else "full"
    return status, round(occupancy, 4)


def status_color(status: str) -> str:
    """狀態對應顏色 HEX"""
    colors = {
        "green": "#2ECC71",
        "yellow": "#F1C40F",
        "red": "#E74C3C",
        "full": "#E74C3C",
        "unknown": "#95A5A6",
    }
    return colors.get(status, "#95A5A6")


def status_label(status: str) -> str:
    """狀態對應中文標籤"""
    labels = {
        "green": "充足",
        "yellow": "偏緊",
        "red": "緊張",
        "full": "滿座",
        "unknown": "未知",
    }
    return labels.get(status, "未知")
