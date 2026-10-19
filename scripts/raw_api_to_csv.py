#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 全 API 原始數據 → CSV（每小時自動快照）

直接從香港政府 / 天文台 API 抓取，唔依賴 SQLite：
  1. 停車場基本資料（static，覆蓋最新一版）
  2. 停車場實時空位（時間序列，追加，保留最近 14 天）
  3. 咪錶分佈（static，覆蓋最新一版）
  4. 咪錶實時佔用（時間序列，追加，保留最近 14 天）
  5. 天文台實時天氣（時間序列，追加，保留最近 14 天）

輸出目錄：data/raw_csv/
每筆快照都帶 snapshot_ts（UTC+8 本地時間），方便離線分析同重現。
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_fetch.carpark_api import (
    fetch_basic_info, fetch_realtime_vacancy, parse_basic_info, parse_vacancy,
)
from src.data_fetch.meter_api import fetch_meter_distribution, fetch_meter_occupancy
from src.data_fetch.weather_api import fetch_current_weather

RAW_DIR = PROJECT_ROOT / "data" / "raw_csv"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 保留天數（與 14 天 Capstone 窗口一致）
KEEP_DAYS = 14


def _now() -> str:
    """統一快照時間戳（香港 UTC+8 用系統本地即可，格式 ISO）"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _prune_14d(df: pd.DataFrame, ts_col: str = "snapshot_ts") -> pd.DataFrame:
    """刪除超過 KEEP_DAYS 天嘅舊快照，控制 CSV 體積"""
    if df.empty or ts_col not in df.columns:
        return df
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    return df[df[ts_col] >= cutoff].reset_index(drop=True)


def _append_series(rows: list[dict], filename: str, dedup_cols: list[str]) -> int:
    """把新快照追加到時間序列 CSV，去重 + 修剪 14 天，回傳寫入行數"""
    path = RAW_DIR / filename
    new_df = pd.DataFrame(rows)
    if new_df.empty:
        print(f"⚠️ {filename}：無新數據，跳過")
        return 0

    if path.exists():
        old = pd.read_csv(path, encoding="utf-8-sig")
        merged = pd.concat([old, new_df], ignore_index=True)
    else:
        merged = new_df

    # 依鍵去重（最新快照覆蓋同 key 舊值）
    merged = merged.drop_duplicates(subset=dedup_cols, keep="last")
    merged = _prune_14d(merged)
    merged.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"✅ {filename}：追加 {len(new_df)} 行，現共 {len(merged)} 行")
    return len(new_df)


def _overwrite_static(rows: list[dict], filename: str) -> int:
    """靜態資料直接覆蓋最新一版"""
    path = RAW_DIR / filename
    df = pd.DataFrame(rows)
    if df.empty:
        print(f"⚠️ {filename}：無數據，保留舊檔")
        return 0
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"✅ {filename}：覆蓋 {len(df)} 行（靜態資料）")
    return len(df)


def main() -> None:
    ts = _now()
    print(f"{'='*60}\n⏰ 全 API 原始快照開始 — {ts}\n{'='*60}")

    # ---------- 1. 停車場基本資料（static）----------
    print("\n[1/5] 停車場基本資料")
    basic_raw = fetch_basic_info()
    basic_rows = [p for p in (parse_basic_info(r) for r in basic_raw) if p]
    _overwrite_static(basic_rows, "carpark_basic.csv")

    # ---------- 2. 停車場實時空位（時間序列）----------
    print("\n[2/5] 停車場實時空位")
    vac_raw = fetch_realtime_vacancy()
    vac_rows = []
    for r in vac_raw:
        p = parse_vacancy(r)
        if p:
            p["snapshot_ts"] = ts
            vac_rows.append(p)
    _append_series(vac_rows, "carpark_vacancy_raw.csv",
                   dedup_cols=["park_id", "snapshot_ts"])

    # ---------- 3. 咪錶分佈（static）----------
    print("\n[3/5] 咪錶分佈")
    meter_dist = fetch_meter_distribution()
    _overwrite_static(meter_dist, "meter_distribution.csv")

    # ---------- 4. 咪錶實時佔用（只保留最新快照，避免每小時11k行撐爆repo）----------
    print("\n[4/5] 咪錶實時佔用")
    meter_occ = fetch_meter_occupancy()
    for m in meter_occ:
        m["snapshot_ts"] = ts
    # 佔用歷史由 DB 同步 workflow 累積，raw CSV 只存最新一版
    _overwrite_static(meter_occ, "meter_occupancy_latest.csv")

    # ---------- 5. 天文台實時天氣（時間序列）----------
    print("\n[5/5] 天文台天氣")
    weather = fetch_current_weather()
    if weather:
        weather["snapshot_ts"] = ts
        _append_series([weather], "weather_raw.csv", dedup_cols=["snapshot_ts"])
    else:
        print("⚠️ 天氣 API 無返回，跳過")

    print(f"\n{'='*60}\n✅ 原始快照完成 → {RAW_DIR}\n{'='*60}")


if __name__ == "__main__":
    main()
