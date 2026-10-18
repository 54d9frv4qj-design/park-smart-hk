# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 時間工具
重新匯出 haversine 模組中的時間函數，保持向後相容
"""
from src.utils.haversine import (
    now_hkt,
    format_hkt,
    is_weekend,
    is_peak_hour,
    get_time_period,
    generate_time_intervals,
    vacancy_status,
    status_color,
    status_label,
)

__all__ = [
    "now_hkt", "format_hkt", "is_weekend", "is_peak_hour",
    "get_time_period", "generate_time_intervals",
    "vacancy_status", "status_color", "status_label",
]
