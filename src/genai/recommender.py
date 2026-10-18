# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 推薦排序引擎
加權排序：距離 + 空位率 + 收費 + 預測趨勢
"""
from typing import List, Dict, Optional
import pandas as pd

from src.utils.haversine import haversine_km, walking_minutes


class ParkingRecommender:
    """停車場推薦排序引擎"""

    def __init__(
        self,
        weight_distance: float = 0.30,
        weight_vacancy: float = 0.30,
        weight_fee: float = 0.20,
        weight_trend: float = 0.20,
    ):
        self.w_distance = weight_distance
        self.w_vacancy = weight_vacancy
        self.w_fee = weight_fee
        self.w_trend = weight_trend

    def recommend(
        self,
        candidates: List[Dict],
        user_lat: float = None,
        user_lng: float = None,
        sort_by: str = "relevance",
        limit: int = 5,
    ) -> List[Dict]:
        """
        推薦停車場
        :param candidates: 候選停車場列表
        :param user_lat/lng: 用戶位置（用於距離排序）
        :param sort_by: 排序方式（relevance/fee/vacancy/distance）
        :param limit: 返回數量
        """
        if not candidates:
            return []

        scored = []
        for cp in candidates:
            score = self._calculate_score(cp, user_lat, user_lng, sort_by)
            cp["recommendation_score"] = round(score, 4)
            cp["recommendation_reason"] = self._generate_reason(cp, sort_by)
            scored.append(cp)

        # 排序
        if sort_by == "fee":
            scored.sort(key=lambda x: x.get("hourly_fee", 999))
        elif sort_by == "vacancy":
            scored.sort(key=lambda x: x.get("vacancy", 0), reverse=True)
        elif sort_by == "distance":
            scored.sort(key=lambda x: x.get("distance_km", 999))
        else:
            scored.sort(key=lambda x: x["recommendation_score"], reverse=True)

        return scored[:limit]

    def _calculate_score(
        self, cp: Dict, user_lat: float, user_lng: float, sort_by: str
    ) -> float:
        """計算推薦分數（0-1）"""
        score = 0.0

        # 空位率分數（越高越好）
        total = cp.get("total_spaces", 100)
        vacancy = cp.get("vacancy", 0)
        vacancy_rate = min(1.0, vacancy / max(total, 1))
        score += self.w_vacancy * vacancy_rate

        # 收費分數（越平越高）
        fee = cp.get("hourly_fee", 50)
        fee_score = max(0, 1 - fee / 60)  # $60 以上 0 分
        score += self.w_fee * fee_score

        # 距離分數（越近越高）
        if user_lat and user_lng and cp.get("lat") and cp.get("lng"):
            dist = haversine_km(user_lat, user_lng, cp["lat"], cp["lng"])
            cp["distance_km"] = round(dist, 2)
            cp["walking_minutes"] = walking_minutes(dist * 1000)
            dist_score = max(0, 1 - dist / 3)  # 3km 以上 0 分
            score += self.w_distance * dist_score
        else:
            score += self.w_distance * 0.5  # 無位置資訊時給中位數

        # 預測趨勢分數
        trend = cp.get("trend", 0)  # 正數=空位增加，負數=減少
        trend_score = 0.5 + trend * 0.1  # 簡單映射
        trend_score = max(0, min(1, trend_score))
        score += self.w_trend * trend_score

        # 滿座懲罰
        if cp.get("status") in ["red", "full"]:
            score *= 0.5

        return score

    def _generate_reason(self, cp: Dict, sort_by: str) -> str:
        """生成推薦原因（港式用語）"""
        reasons = []
        status = cp.get("status", "unknown")

        if status == "green":
            reasons.append("而家空位充足")
        elif status == "yellow":
            reasons.append("而家仲有少量位")
        elif status in ["red", "full"]:
            reasons.append("而家比較緊張")

        if cp.get("distance_km"):
            if cp["distance_km"] < 0.5:
                reasons.append(f"離你好近（{cp['distance_km']}km）")
            elif cp["distance_km"] < 1:
                reasons.append(f"步行可到（{cp.get('walking_minutes', '?')}分鐘）")

        if cp.get("hourly_fee"):
            if cp["hourly_fee"] < 20:
                reasons.append(f"時租好平（HK${cp['hourly_fee']:.0f}）")
            elif cp["hourly_fee"] > 40:
                reasons.append(f"時租偏貴（HK${cp['hourly_fee']:.0f}）")

        if cp.get("has_ev_charging"):
            reasons.append("有EV充電")

        if cp.get("is_government"):
            reasons.append("政府停車場")

        return "、".join(reasons[:3]) if reasons else "綜合推薦"


def find_alternatives(
    target_carpark: Dict,
    all_carparks: List[Dict],
    radius_km: float = 1.0,
    limit: int = 5,
) -> List[Dict]:
    """
    尋找替代停車場
    :param target_carpark: 目標停車場（已滿或用戶想找替代）
    :param all_carparks: 所有停車場
    :param radius_km: 搜尋半徑
    :param limit: 返回數量
    """
    if not target_carpark or not all_carparks:
        return []

    lat, lng = target_carpark.get("lat"), target_carpark.get("lng")
    if not lat or not lng:
        return []

    # 過濾方圓內的停車場（排除自己）
    nearby = []
    for cp in all_carparks:
        if cp.get("park_id") == target_carpark.get("park_id"):
            continue
        if not cp.get("lat") or not cp.get("lng"):
            continue
        dist = haversine_km(lat, lng, cp["lat"], cp["lng"])
        if dist <= radius_km:
            cp["distance_km"] = round(dist, 2)
            cp["walking_minutes"] = walking_minutes(dist * 1000)
            nearby.append(cp)

    # 按空位率排序（優先推薦有位嘅）
    nearby.sort(
        key=lambda x: (
            x.get("status") != "green",  # green 優先
            -x.get("vacancy", 0),         # 空位多優先
            x.get("distance_km", 999),    # 近優先
        )
    )

    return nearby[:limit]


# 全局推薦器實例
_recommender = ParkingRecommender()


def recommend_parking(candidates: List[Dict], **kwargs) -> List[Dict]:
    """便捷函數：推薦停車場"""
    return _recommender.recommend(candidates, **kwargs)
