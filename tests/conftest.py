# -*- coding: utf-8 -*-
"""pytest 共享 fixture。"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_carpark():
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
