# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — pytest 配置與共享 fixture
"""
import sys
from pathlib import Path

import pytest

# 確保項目根目錄在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def engine():
    """建立測試用資料庫（含模擬數據）"""
    from src.db.connection import get_engine, init_db
    from src.mock_data.carpark_generator import generate_mock_carparks
    from src.mock_data.meter_generator import generate_mock_meters
    from src.mock_data.weather_generator import generate_mock_weather

    engine = get_engine()
    init_db(engine)

    # 檢查是否已有數據
    from sqlalchemy import text
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM carparks_static")).scalar()

    if count == 0:
        # 生成少量模擬數據用於測試
        generate_mock_carparks(engine, count=20, days=2)
        generate_mock_meters(engine, count=10, days=2)
        generate_mock_weather(engine, days=2)

    return engine


@pytest.fixture
def sample_carpark():
    """示例停車場數據"""
    return {
        "park_id": "TEST001",
        "name": "測試停車場",
        "district": "中西區",
        "lat": 22.2855,
        "lng": 114.1610,
        "total_spaces": 100,
        "vacancy": 35,
        "occupancy_rate": 0.65,
        "status": "green",
        "hourly_fee": 30,
    }


@pytest.fixture
def sample_query():
    """示例查詢"""
    return "而家旺角邊度有位泊？"
