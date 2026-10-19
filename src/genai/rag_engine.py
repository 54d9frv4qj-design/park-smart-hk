# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — RAG 檢索增強對話引擎
LangChain 風格：規則 + 檢索 + 生成
"""
from typing import Dict, List, Optional
from datetime import datetime

from src.genai.query_parser import parse_query
from src.genai.recommender import recommend_parking, find_alternatives
from src.genai.response_generator import generate_response
from src.db.connection import get_engine
from src.db.queries import (
    search_carparks, get_all_latest_status, get_all_meters_latest,
    get_nearby_carparks, get_overview_stats, get_fee_comparison,
    get_latest_weather,
)
from src.utils.logger import log


class ParkingAssistant:
    """
    泊車助手：完整對話管線
    query_parser → retriever → recommender → response_generator
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()

    def chat(self, message: str, history: List[Dict] = None) -> Dict:
        """
        處理用戶訊息，返回完整回應
        :param message: 用戶輸入
        :param history: 對話歷史
        :return: {response, intent, entities, recommendations, metadata}
        """
        start_time = datetime.now()
        history = history or []

        log.info(f"💬 用戶：{message}")

        # 1. 解析查詢
        parsed = parse_query(message)
        intent = parsed["intent"]
        entities = parsed["entities"]
        log.info(f"   意圖：{intent}（信心：{parsed['confidence']:.0%}）")

        # 2. 檢索數據
        recommendations = self._retrieve(intent, entities)

        # 3. 上下文（天氣、統計）
        context = self._build_context(intent)

        # 4. 生成回應
        response = generate_response(intent, entities, recommendations, context=context)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        log.info(f"   回應耗時：{elapsed:.0f}ms")

        return {
            "response": response,
            "intent": intent,
            "entities": entities,
            "recommendations": recommendations,
            "confidence": parsed["confidence"],
            "response_time_ms": round(elapsed, 1),
        }

    def _retrieve(self, intent: str, entities: Dict) -> List[Dict]:
        """根據意圖檢索相關數據"""
        district = entities.get("district", "")
        sort_by = entities.get("sort_by", "relevance")

        try:
            if intent == "find_meter":
                return self._retrieve_meters(district)

            if intent == "check_fee" or intent == "compare_fee":
                return self._retrieve_fees(district, sort_by)

            if intent == "dashboard_stats":
                return []

            # 默認：搵停車場
            return self._retrieve_carparks(district, sort_by, entities)

        except Exception as e:
            log.error(f"檢索失敗：{e}")
            return []

    def _retrieve_carparks(self, district: str, sort_by: str, entities: Dict) -> List[Dict]:
        """檢索停車場"""
        # 搜尋
        if district:
            df = search_carparks(self.engine, district=district)
            raw = entities.get("district_raw", "")
            if raw:
                local = df[
                    df["name"].fillna("").str.contains(raw, na=False)
                    | df["address"].fillna("").str.contains(raw, na=False)
                ]
                if not local.empty:
                    df = local
        else:
            df = get_all_latest_status(self.engine)

        if df.empty:
            return []

        # 轉為 dict 列表
        candidates = df.to_dict("records")

        # 推薦排序
        return recommend_parking(
            candidates,
            sort_by=sort_by,
            limit=5,
        )

    def _retrieve_meters(self, district: str) -> List[Dict]:
        """檢索咪錶"""
        df = get_all_meters_latest(self.engine)
        if df.empty:
            return []
        if district:
            df = df[df["district"] == district]
        return df.head(5).to_dict("records")

    def _retrieve_fees(self, district: str, sort_by: str) -> List[Dict]:
        """檢索收費"""
        df = get_fee_comparison(
            self.engine,
            district=district,
            sort_by="hourly_fee" if sort_by == "fee" else "hourly_fee",
        )
        if df.empty:
            return []
        return df.head(5).to_dict("records")

    def _build_context(self, intent: str) -> Dict:
        """建立上下文（天氣、統計）"""
        context = {}
        try:
            if intent == "dashboard_stats":
                context.update(get_overview_stats(self.engine))

            weather = get_latest_weather(self.engine)
            if weather:
                context["weather"] = {
                    "temp": weather.get("temperature"),
                    "rain": weather.get("rainfall", 0),
                    "desc": weather.get("weather_desc", ""),
                }
        except Exception as e:
            log.warning(f"上下文建立失敗：{e}")
        return context


# 全局助手實例
_assistant = None


def get_assistant() -> ParkingAssistant:
    """取得全局助手實例"""
    global _assistant
    if _assistant is None:
        _assistant = ParkingAssistant()
    return _assistant


def chat(message: str, history: List[Dict] = None) -> Dict:
    """便捷函數：對話"""
    return get_assistant().chat(message, history)
