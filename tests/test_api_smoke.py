# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — FastAPI 冒煙測試
驗證 9 個端點全部可訪問、返回 200、JSON 格式正確
"""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestAPISmoke:
    """API 冒煙測試"""

    def test_root(self):
        """測試根路徑"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "app" in data
        assert "version" in data

    def test_health(self):
        """測試健康檢查"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_overview(self):
        """測試 /api/overview"""
        resp = client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_carparks" in data
        assert "avg_occupancy" in data

    def test_map(self):
        """測試 /api/map"""
        resp = client.get("/api/map")
        assert resp.status_code == 200
        data = resp.json()
        assert "points" in data
        assert "count" in data

    def test_map_with_district(self):
        """測試 /api/map 帶地區參數"""
        resp = client.get("/api/map", params={"district": "中西區"})
        assert resp.status_code == 200

    def test_detail(self, engine):
        """測試 /api/detail/{park_id}"""
        # 先取得一個存在的 park_id
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(text("SELECT park_id FROM carparks_static LIMIT 1")).fetchone()
        if row:
            park_id = row[0]
            resp = client.get(f"/api/detail/{park_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["park_id"] == park_id

    def test_detail_not_found(self):
        """測試不存在的停車場"""
        resp = client.get("/api/detail/NONEXISTENT")
        assert resp.status_code == 404

    def test_alternatives(self, engine):
        """測試 /api/alternatives/{park_id}"""
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(text("SELECT park_id FROM carparks_static LIMIT 1")).fetchone()
        if row:
            park_id = row[0]
            resp = client.get(f"/api/alternatives/{park_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert "alternatives" in data

    def test_meters(self):
        """測試 /api/meters"""
        resp = client.get("/api/meters")
        assert resp.status_code == 200
        data = resp.json()
        assert "meters" in data

    def test_dashboard(self):
        """測試 /api/dashboard"""
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "overview" in data
        assert "district_ranking" in data

    def test_search(self):
        """測試 /api/search"""
        resp = client.get("/api/search", params={"q": "停車場"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_chat(self):
        """測試 /api/chat"""
        resp = client.post("/api/chat", json={"message": "你好"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "intent" in data

    def test_fees(self):
        """測試 /api/fees"""
        resp = client.get("/api/fees")
        assert resp.status_code == 200
        data = resp.json()
        assert "fees" in data

    def test_openapi_docs(self):
        """測試 OpenAPI 文檔"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert "paths" in resp.json()
