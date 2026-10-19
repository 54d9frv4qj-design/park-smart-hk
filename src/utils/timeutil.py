# -*- coding: utf-8 -*-
"""統一香港時間（UTC+8）。

伺服器（GitHub Actions / Streamlit Cloud）預設係 UTC，直接用 datetime.now()
會慢 8 小時，令「最近 N 小時」「今日」「當前小時」同 API 嘅香港時間錯位。
所有需要「而家」嘅地方一律用本模組。
"""
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    _HKT = ZoneInfo("Asia/Hong_Kong")
except Exception:  # 冇 tzdata 時退回固定 +8（香港無夏令時）
    _HKT = timezone(timedelta(hours=8))


def hkt_now() -> datetime:
    """當前香港時間（帶時區）。"""
    return datetime.now(_HKT)


def hkt_now_str() -> str:
    """當前香港時間字串 YYYY-MM-DD HH:MM:SS。"""
    return hkt_now().strftime("%Y-%m-%d %H:%M:%S")
