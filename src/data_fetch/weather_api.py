# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 香港天文台 API 抓取
對接 HKO Open Data：實時天氣、警告訊息
"""
import time
from typing import Dict, Optional

import requests

from src.config import (
    HKO_WEATHER_URL,
    API_TIMEOUT, API_RATE_LIMIT_SECONDS, API_HEADERS,
)
from src.utils.logger import log


def fetch_current_weather() -> Optional[Dict]:
    """
    抓取香港天文台實時天氣
    API: data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc
    返回：含氣溫、濕度、雨量、天氣描述
    """
    log.info(f"📡 抓取天文台實時天氣：{HKO_WEATHER_URL}")
    try:
        resp = requests.get(
            HKO_WEATHER_URL,
            headers=API_HEADERS,
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        # 解析 HKO 格式
        temperature = None
        humidity = None
        rainfall = 0.0
        weather_desc = ""

        # 氣溫（取第一個分區或平均值）
        temp_data = data.get("temperature", {}).get("data", [])
        if temp_data:
            temperatures = [t.get("value") for t in temp_data if t.get("value") is not None]
            if temperatures:
                temperature = sum(temperatures) / len(temperatures)

        # 濕度
        humidity_data = data.get("humidity", {}).get("data", [])
        if humidity_data:
            humidity = humidity_data[0].get("value")

        # 雨量
        rain_data = data.get("rainfall", {}).get("data", [])
        if rain_data:
            rainfalls = [r.get("max", 0) for r in rain_data if r.get("max") is not None]
            rainfall = max(rainfalls) if rainfalls else 0

        # 天氣描述
        icon = data.get("icon", [0])
        weather_desc = _hko_icon_to_desc(icon[0] if icon else 0)

        result = {
            "temperature": round(temperature, 1) if temperature else None,
            "humidity": humidity,
            "rainfall": rainfall,
            "weather_icon": icon[0] if icon else 0,
            "weather_desc": weather_desc,
            "snapshot_time": data.get("updateTime", ""),
        }
        log.info(f"✅ 天氣：{weather_desc}，{temperature}°C，濕度 {humidity}%")
        return result

    except Exception as e:
        log.error(f"❌ 抓取天氣失敗：{e}")
        return None
    finally:
        time.sleep(API_RATE_LIMIT_SECONDS)


def _hko_icon_to_desc(icon: int) -> str:
    """HKO 天氣圖示代碼轉中文描述"""
    mapping = {
        1: "晴", 2: "間晴", 3: "多雲",
        5: "間有驟雨", 6: "有驟雨", 7: "有雨",
        8: "大雨", 9: "雷暴",
        10: "乾燥", 11: "潮濕", 12: "霧",
        13: "薄霧", 14: "煙霞",
        15: "大風", 16: "烈風",
        20: "冷", 21: "熱",
        22: "顯著降溫", 23: "霜", 24: "冰",
        25: "雪", 26: "積雪",
        27: "閃電", 28: "雷",
        30: "月圓", 31: "月缺", 32: "新月",
        33: "日間", 34: "夜間",
        35: "紫外線指數高",
        36: "漲潮", 37: "退潮",
        38: "洪水", 39: "山泥傾瀉",
        40: "火災危險",
        41: "空氣污染",
        42: "寒冷天氣警告",
        43: "酷熱天氣警告",
        44: "霜凍警告",
        45: "強季候風信號",
        46: "雷暴警告",
        47: "山泥傾瀉警告",
        48: "新界北部水浸特別報告",
        49: "熱帶氣旋警告",
        50: "暴雨警告",
        51: "黑色暴雨警告",
        52: "紅色暴雨警告",
        53: "黃色暴雨警告",
    }
    return mapping.get(icon, "多雲")
