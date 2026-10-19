# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — ETL 管線測試
"""
import pytest
from src.etl.cleaners import clean_carpark_data, clean_meter_data, clean_weather_data
from src.utils.haversine import haversine_km, vacancy_status


class TestCleaners:
    """數據清洗測試"""

    def test_clean_carpark_data(self, sample_carpark):
        """測試停車場數據清洗"""
        cleaned = clean_carpark_data(sample_carpark)
        assert cleaned["park_id"] == "TEST001"
        assert cleaned["vacancy"] == 35
        assert 0 <= cleaned["occupancy_rate"] <= 1
        assert cleaned["status"] in ["green", "yellow", "red", "full"]

    def test_clean_carpark_negative_vacancy(self):
        """測試負數空位處理"""
        raw = {"park_id": "T1", "vacancy": -5, "total_spaces": 100}
        cleaned = clean_carpark_data(raw)
        assert cleaned["vacancy"] == 0

    def test_clean_carpark_missing(self):
        """測試缺失值處理"""
        raw = {"park_id": "T1"}
        cleaned = clean_carpark_data(raw)
        assert cleaned["vacancy"] == 0
        assert cleaned["park_id"] == "T1"

    def test_clean_meter_data(self):
        """測試咪錶數據清洗"""
        raw = {"meter_id": "M001", "status_raw": "V", "total_spaces": 4}
        cleaned = clean_meter_data(raw)
        assert cleaned["meter_id"] == "M001"
        assert cleaned["vacant_spaces"] == 4
        assert cleaned["occupied_spaces"] == 0

    def test_clean_meter_occupied(self):
        """測試咪錶佔用狀態"""
        raw = {"meter_id": "M001", "status_raw": "O", "total_spaces": 4}
        cleaned = clean_meter_data(raw)
        assert cleaned["vacant_spaces"] == 0
        assert cleaned["occupied_spaces"] == 4

    def test_clean_weather_data(self):
        """測試天氣數據清洗"""
        raw = {"temperature": 28.5, "humidity": 80, "rainfall": 5.2, "weather_desc": "大雨"}
        cleaned = clean_weather_data(raw)
        assert cleaned["temperature"] == 28.5
        assert cleaned["humidity"] == 80
        assert cleaned["rainfall"] == 5.2

    def test_clean_weather_invalid_temp(self):
        """測試異常氣溫處理"""
        raw = {"temperature": 150, "humidity": 80}
        cleaned = clean_weather_data(raw)
        assert cleaned["temperature"] is None  # 超出合理範圍


class TestHaversine:
    """Haversine 距離測試"""

    def test_haversine_km(self):
        """測試球面距離計算"""
        # 中環到尖沙咀大約 1.5km
        dist = haversine_km(22.2855, 114.1610, 22.2970, 114.1720)
        assert 1.0 < dist < 2.5

    def test_haversine_same_point(self):
        """測試同一點距離為 0"""
        dist = haversine_km(22.2855, 114.1610, 22.2855, 114.1610)
        assert dist < 0.001


class TestVacancyStatus:
    """空位狀態測試"""

    def test_status_green(self):
        """測試充足狀態"""
        status, occ = vacancy_status(50, 100)
        assert status == "green"

    def test_status_yellow(self):
        """測試偏緊狀態"""
        status, occ = vacancy_status(15, 100)
        assert status == "yellow"

    def test_status_red(self):
        """測試緊張狀態"""
        status, occ = vacancy_status(5, 100)
        assert status == "red"

    def test_status_full(self):
        """測試滿座狀態"""
        status, occ = vacancy_status(0, 100)
        assert status == "full"
