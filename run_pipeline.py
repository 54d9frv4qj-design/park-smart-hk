# -*- coding: utf-8 -*-
"""
run_pipeline.py —— 一鍵執行整條資料管線
========================================
  1. 抓取數據（停車場 / 咪錶 / 天氣）
  2. ETL 清洗
  3. 寫入 SQLite
  4. （可選）訓練模型並存成 .pkl

用法：
    python run_pipeline.py              # 只做 抓取 -> 清洗 -> 寫庫
    python run_pipeline.py --train      # 抓取後再訓練分類 + 回歸模型
"""
from __future__ import annotations
import argparse

from src.data_fetch import carpark_api, meter_weather_api
from src.etl.etl_pipeline import run_etl
from src.db.db_writer import get_engine, init_db, write_to_db


def fetch_all() -> dict:
    """抓取全部數據源，回傳原始 DataFrame dict。"""
    print("==> 1/3 抓取停車場數據 ...")
    carparks = carpark_api.fetch_carpark_all()

    print("==> 抓取咪錶數據 ...")
    meters = meter_weather_api.fetch_meter_all()

    print("==> 抓取天氣數據 ...")
    weather_df = meter_weather_api.fetch_weather(verbose=True)

    return {**carparks, **meters, "weather": weather_df}


def main() -> None:
    parser = argparse.ArgumentParser(description="香港智能停車 ETL 管線")
    parser.add_argument("--train", action="store_true",
                        help="寫庫後一併訓練模型")
    args = parser.parse_args()

    # 1) 抓取
    raw = fetch_all()

    # 2) ETL 清洗
    print("\n==> 2/3 清洗數據 ...")
    clean = run_etl(raw)

    # 3) 寫入 SQLite
    print("\n==> 3/3 寫入 SQLite ...")
    engine = get_engine()
    init_db(engine)
    write_to_db(engine, clean)

    print("\n[完成] 數據管線執行完畢，數據庫位於 data/smart_parking.db")

    # 4) 可選：訓練模型
    if args.train:
        print("\n==> 訓練模型 ...")
        from src.models.train_classifier import train_classifier
        from src.models.train_regressor import train_regressor
        train_classifier(engine)
        train_regressor(engine, horizon_min=30)
        train_regressor(engine, horizon_min=60)
        print("\n[完成] 模型已儲存至 models/")


if __name__ == "__main__":
    main()
