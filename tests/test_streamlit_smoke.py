# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — Streamlit AppTest 冒煙測試
驗證 8 個頁面全部可渲染、無異常
"""
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAMLIT_APP = PROJECT_ROOT / "streamlit_app"


class TestStreamlitSmoke:
    """Streamlit 8 頁冒煙測試"""

    def test_home_page(self):
        """測試首頁可渲染"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "Home.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"首頁異常：{at.exception}"

    def test_realtime_map_page(self):
        """測試實時地圖頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "1_實時地圖.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"實時地圖頁異常：{at.exception}"

    def test_carpark_detail_page(self):
        """測試停車場詳情頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "2_停車場詳情.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"停車場詳情頁異常：{at.exception}"

    def test_ai_chat_page(self):
        """測試 AI 對話頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "3_AI對話.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"AI 對話頁異常：{at.exception}"

    def test_meter_page(self):
        """測試路邊咪錶頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "4_路邊咪錶.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"路邊咪錶頁異常：{at.exception}"

    def test_dashboard_page(self):
        """測試儀表板頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "5_儀表板.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"儀表板頁異常：{at.exception}"

    def test_fee_comparison_page(self):
        """測試收費比較頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "6_收費比較.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"收費比較頁異常：{at.exception}"

    def test_about_page(self):
        """測試關於頁"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(STREAMLIT_APP / "pages" / "7_關於.py"), default_timeout=30)
        at.run()
        assert not at.exception, f"關於頁異常：{at.exception}"
