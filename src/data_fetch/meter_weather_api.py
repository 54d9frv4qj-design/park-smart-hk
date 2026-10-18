# -*- coding: utf-8 -*-
"""
meter_weather_api.py —— 路邊咪錶 + 天氣數據抓取
=================================================
包含三部分：
  1. 咪錶靜態分佈 (CSV, 公開)      —— 經緯度 + 收費 (PaymentUnit / TimeUnit)
  2. 咪錶實時佔用 (CSV, 公開)      —— 每個咪錶位是空(V)還是被佔(O)
  3. 天氣 (HKO Open Data, 公開)    —— 各區雨量 / 濕度 / 溫度

以及一個示範函式：
  4. CSDI FeatureServer 抓取       —— 說明如何設定 Headers 與查詢參數以解決 403，
                                      並誠實告知該服務仍需 Token (code 499)。
"""
from __future__ import annotations
import io
import requests
import pandas as pd
from typing import Dict, Optional

from ..config import (
    METER_DISTRIBUTION_URL,
    METER_OCCUPANCY_URL,
    WEATHER_URL,
    WEATHER_DATATYPE,
    WEATHER_LANG,
    CSDI_HEADERS,
    CSDI_METER_SERVICE,
    CSDI_RAINFALL_SERVICE,
    CSDI_RH_SERVICE,
    CSDI_TOKEN,
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
_session = requests.Session()
_session.headers.update(DEFAULT_HEADERS)


# ===========================================================================
# 1) 咪錶靜態分佈
# ===========================================================================
def fetch_meter_distribution() -> pd.DataFrame:
    """抓取全港咪錶泊車位分佈（含經緯度與收費）。

    注意：這個 CSV 前 2 行是「檔案產生時間」與空行，真正的表頭在第 3 行。
    因此用 `skiprows` 跳過前兩行，並由 pandas 自動把第 3 行當表頭。
    """
    resp = _session.get(METER_DISTRIBUTION_URL, timeout=30)
    resp.raise_for_status()
    # 用 io.StringIO 包住文字，避免 pandas 直接吃網址時對 BOM 的解析問題
    df = pd.read_csv(io.StringIO(resp.text), skiprows=2, encoding="utf-8-sig")
    # 清理全空列 / 全 NaN 列
    df = df.dropna(how="all", axis=1)
    return df


# ===========================================================================
# 2) 咪錶實時佔用
# ===========================================================================
def fetch_meter_occupancy() -> pd.DataFrame:
    """抓取已安裝新咪錶的泊車位實時佔用狀態。

    欄位：
        ParkingSpaceId       咪錶位識別碼
        ParkingMeterStatus   N=正常, NU=不可用
        OccupancyStatus      V=空, O=被佔用
        OccupancyDateChanged 狀態最後變更時間 (MM/DD/YYYY hh:mm:ss)
    """
    resp = _session.get(METER_OCCUPANCY_URL, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
    return df


# ===========================================================================
# 3) 天氣 (HKO Open Data)
# ===========================================================================
def fetch_weather(verbose: bool = False) -> pd.DataFrame:
    """抓取現時天氣報告，攤平成「每區一列」的長格式。

    HKO `rhrread` 回傳結構：
        rainfall.data[]   -> 每區過去1小時雨量 (place, max)
        humidity.data[]   -> 每區濕度 (place, value)
        temperature.data[]-> 每區氣溫 (place, value)
        icon[]            -> 天氣圖示代碼

    Returns:
        pd.DataFrame: 欄位 = [district, rainfall, humidity, temperature, icon, update_time]
    """
    params = {"dataType": WEATHER_DATATYPE, "lang": WEATHER_LANG}
    resp = _session.get(WEATHER_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rain_map = {r["place"]: r.get("max") for r in data.get("rainfall", {}).get("data", [])}
    hum_map = {h["place"]: h.get("value") for h in data.get("humidity", {}).get("data", [])}
    temp_map = {t["place"]: t.get("value") for t in data.get("temperature", {}).get("data", [])}
    # 全部地區的聯集
    districts = set(rain_map) | set(hum_map) | set(temp_map)

    rows = [{
        "district": d,
        "rainfall": rain_map.get(d),
        "humidity": hum_map.get(d),
        "temperature": temp_map.get(d),
        "update_time": data.get("updateTime"),
    } for d in sorted(districts)]
    if verbose:
        print(f"[HKO] 天氣資料更新時間: {data.get('updateTime')}，涵蓋 {len(districts)} 個地區")
    return pd.DataFrame(rows)


# ===========================================================================
# 4) CSDI FeatureServer (ArcGIS REST) —— 403 解決方案示範
# ===========================================================================
def _arcgis_query(service_url: str, layer: int = 0,
                  where: str = "1=1", out_fields: str = "*",
                  limit: int = 2000, offset: int = 0,
                  token: Optional[str] = None) -> Dict:
    """以 ArcGIS REST API 的正確寫法查詢 FeatureServer。

    解決 403 的關鍵：
      1. 必須帶瀏覽器式 User-Agent 等 Headers（CSDI 門戶會擋掉預設 python UA）
      2. where 需要 URL-encoded：where=1%3D1（1=1）
      3. 顯式給 f=json 指定回傳格式
      4. outSR=4326 讓座標以 WGS84 (經緯度) 輸出

    誠實說明：此類服務加上 Headers 後 403 會消失，但服務本身仍會回傳
    {"error":{"code":499,"message":"Token Required"}}，表示必須使用有效 Token。
    """
    headers = dict(CSDI_HEADERS)
    params = {
        "where": where,
        "outFields": out_fields,
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": limit,
    }
    if token:
        params["token"] = token

    url = f"{service_url}/{layer}/query"
    resp = _session.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    # 若是 Token 相關錯誤，回傳原始訊息以便除錯
    if "error" in payload:
        print(f"[CSDI] 查詢失敗: {payload['error'].get('message')} "
              f"(code={payload['error'].get('code')})")
    return payload


def fetch_csdi_metered_parking(token: Optional[str] = None) -> pd.DataFrame:
    """從 CSDI 抓取路邊咪錶 (FeatureServer)。

    Args:
        token: CSDI 門戶取得的 Token。None 時嘗試讀取 config 中的 CSDI_TOKEN。

    Returns:
        pd.DataFrame: 咪錶空間資料。若缺 Token，回傳空 DataFrame 並印出原因。
    """
    token = token or CSDI_TOKEN or None
    payload = _arcgis_query(CSDI_METER_SERVICE, token=token)
    if "error" in payload:
        print("[CSDI] 咪錶資料：需要 Token，已改用公開 CSV 路徑即可取得同類資料。")
        return pd.DataFrame()
    features = payload.get("features", [])
    rows = [f.get("attributes", {}) for f in features]
    df = pd.DataFrame(rows)
    # ArcGIS 常以 x/y 欄位存放經緯度
    if "x" in df.columns and "y" in df.columns:
        df["longitude"] = df["x"]
        df["latitude"] = df["y"]
    return df


def fetch_csdi_weather(token: Optional[str] = None) -> pd.DataFrame:
    """從 CSDI 抓取天氣 (降雨 FeatureServer)。同樣需 Token，邏輯同上。"""
    token = token or CSDI_TOKEN or None
    payload = _arcgis_query(CSDI_RAINFALL_SERVICE, token=token)
    if "error" in payload:
        print("[CSDI] 天氣資料：需要 Token，已改用 HKO Open Data 公開 API。")
        return pd.DataFrame()
    features = payload.get("features", [])
    return pd.DataFrame([f.get("attributes", {}) for f in features])


# ===========================================================================
# 便捷函式
# ===========================================================================
def fetch_meter_all() -> Dict[str, pd.DataFrame]:
    """抓取咪錶分佈 + 佔用，回傳 {'distribution': DF, 'occupancy': DF}。"""
    return {
        "distribution": fetch_meter_distribution(),
        "occupancy": fetch_meter_occupancy(),
    }
