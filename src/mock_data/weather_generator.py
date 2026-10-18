# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 天氣模擬數據生成器
模擬香港天文台格式：氣溫、濕度、雨量、天氣描述、警告
"""
import random
import math
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import MOCK_HISTORY_DAYS

random.seed(789)

# 香港天氣類型
WEATHER_TYPES = [
    (1, "晴", 0.0),
    (2, "間晴", 0.0),
    (3, "多雲", 0.0),
    (5, "間有驟雨", 2.0),
    (6, "有驟雨", 5.0),
    (7, "有雨", 8.0),
    (8, "大雨", 15.0),
    (9, "雷暴", 10.0),
]

# 香港季節平均氣溫（按月）
MONTHLY_AVG_TEMP = {
    1: 16, 2: 17, 3: 19, 4: 23, 5: 26, 6: 28,
    7: 29, 8: 29, 9: 28, 10: 25, 11: 21, 12: 17,
}


def _generate_weather_record(dt: datetime) -> Dict:
    """生成單個天氣記錄"""
    month = dt.month
    hour = dt.hour

    # 氣溫：日間高，夜間低
    base_temp = MONTHLY_AVG_TEMP.get(month, 24)
    diurnal = 4 * math.sin((hour - 6) / 24 * 2 * math.pi)
    temperature = round(base_temp + diurnal + random.gauss(0, 1.5), 1)

    # 濕度：香港普遍高濕
    humidity = round(random.uniform(65, 95), 0)

    # 降雨：隨機選擇天氣類型
    rain_prob = 0.3 if month in [4, 5, 6, 7, 8, 9] else 0.15
    if random.random() < rain_prob:
        weather = random.choice(WEATHER_TYPES[3:])
    else:
        weather = random.choice(WEATHER_TYPES[:3])

    rainfall = round(weather[2] * random.uniform(0.5, 1.5) if weather[2] > 0 else 0, 1)

    # 天氣警告：大雨/颱風季節有機會
    has_warning = 0
    warning_type = ""
    if rainfall > 10 and random.random() < 0.3:
        has_warning = 1
        warning_type = random.choice(["黃色暴雨警告", "紅色暴雨警告", "黑色暴雨警告"])
    elif month in [7, 8, 9] and random.random() < 0.02:
        has_warning = 1
        warning_type = random.choice(["一號戒備信號", "三號強風信號", "八號東南烈風信號"])

    # 紫外線
    uv_index = round(max(0, 8 * math.sin((hour - 6) / 12 * math.pi)) + random.gauss(0, 1), 1) if 6 <= hour <= 18 else 0

    return {
        "snapshot_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "district": "全港",
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "weather_icon": weather[0],
        "weather_desc": weather[1],
        "has_warning": has_warning,
        "warning_type": warning_type,
        "uv_index": uv_index,
    }


def generate_mock_weather(engine: Engine, days: int = None) -> None:
    """生成模擬天氣數據並寫入 DB（每小時一筆）"""
    days = days or MOCK_HISTORY_DAYS
    print(f"[Mock] 生成 {days} 天天氣數據...")

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    records = []
    current = start_time
    while current <= end_time:
        records.append(_generate_weather_record(current))
        current += timedelta(hours=1)

    # 批量寫入
    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        with engine.connect() as conn:
            conn.execute(text(
                """
                INSERT INTO weather_data
                    (snapshot_time, district, temperature, humidity, rainfall,
                     weather_icon, weather_desc, has_warning, warning_type, uv_index)
                VALUES
                    (:snapshot_time, :district, :temperature, :humidity, :rainfall,
                     :weather_icon, :weather_desc, :has_warning, :warning_type, :uv_index)
                """
            ), batch)
            conn.commit()

    print(f"[Mock] 天氣數據寫入完成：{len(records)} 筆")
