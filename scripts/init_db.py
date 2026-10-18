#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 資料庫初始化腳本
用法：
    python scripts/init_db.py           # 建立空 Schema
    python scripts/init_db.py --mock    # 建立 Schema 並填入模擬數據
"""
import argparse
import os
import sys
from pathlib import Path

# 將項目根目錄加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from src.db.connection import get_engine, init_db
from src.mock_data.carpark_generator import generate_mock_carparks
from src.mock_data.meter_generator import generate_mock_meters
from src.mock_data.weather_generator import generate_mock_weather


def main():
    parser = argparse.ArgumentParser(description="初始化泊得好資料庫")
    parser.add_argument("--mock", action="store_true", help="填入模擬數據（離線可運行）")
    parser.add_argument("--carparks", type=int, default=607, help="模擬停車場數量")
    parser.add_argument("--meters", type=int, default=200, help="模擬咪錶組數量")
    parser.add_argument("--days", type=int, default=30, help="模擬歷史天數")
    args = parser.parse_args()

    logger.info("🚀 開始初始化資料庫...")

    # 1. 建立 Schema
    engine = get_engine()
    init_db(engine)
    logger.info("✅ 資料庫 Schema 建立完成")

    # 2. 選擇性填入模擬數據
    if args.mock:
        logger.info(f"📊 產生模擬數據：{args.carparks} 停車場 + {args.meters} 咪錶組 + {args.days} 天歷史")
        generate_mock_carparks(engine, count=args.carparks, days=args.days)
        generate_mock_meters(engine, count=args.meters, days=args.days)
        generate_mock_weather(engine, days=args.days)
        logger.info("✅ 模擬數據填入完成")

    logger.info("🎉 資料庫初始化完畢！")


if __name__ == "__main__":
    main()
