# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — Pydantic 請求/響應模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# 通用響應
# ============================================================
class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None


# ============================================================
# 總覽
# ============================================================
class OverviewResponse(BaseModel):
    total_carparks: int = 0
    total_spaces: int = 0
    avg_occupancy: float = 0.0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0
    total_meters: int = 0
    update_time: str = ""


# ============================================================
# 地圖
# ============================================================
class MapPoint(BaseModel):
    park_id: str
    name: str
    district: str
    lat: float
    lng: float
    vacancy: Optional[int] = None
    total_spaces: int = 0
    occupancy_rate: Optional[float] = None
    status: str = "unknown"
    hourly_fee: Optional[float] = None


class MapResponse(BaseModel):
    points: List[MapPoint] = []
    count: int = 0


# ============================================================
# 停車場詳情
# ============================================================
class CarparkDetail(BaseModel):
    park_id: str
    name: str
    name_en: Optional[str] = None
    district: str
    address: Optional[str] = None
    lat: float
    lng: float
    total_spaces: int = 0
    ev_spaces: int = 0
    vacancy: Optional[int] = None
    occupancy_rate: Optional[float] = None
    status: str = "unknown"
    hourly_fee: Optional[float] = None
    daily_fee: Optional[float] = None
    monthly_fee: Optional[float] = None
    is_government: int = 0
    has_ev_charging: int = 0
    prediction_30min: Optional[int] = None
    prediction_60min: Optional[int] = None
    update_time: str = ""


# ============================================================
# 替代推薦
# ============================================================
class AlternativeCarpark(BaseModel):
    park_id: str
    name: str
    distance_km: float
    walking_minutes: float
    vacancy: Optional[int] = None
    occupancy_rate: Optional[float] = None
    status: str = "unknown"
    hourly_fee: Optional[float] = None


class AlternativesResponse(BaseModel):
    target_park_id: str
    alternatives: List[AlternativeCarpark] = []


# ============================================================
# 咪錶
# ============================================================
class MeterInfo(BaseModel):
    meter_id: str
    street_name: Optional[str] = None
    district: str
    lat: float
    lng: float
    total_spaces: int = 0
    vacant_spaces: Optional[int] = None
    occupancy_rate: Optional[float] = None
    status: str = "unknown"
    hourly_fee: Optional[float] = None
    max_duration: int = 120
    is_interpolated: int = 0


# ============================================================
# 儀表板
# ============================================================
class DistrictRank(BaseModel):
    district: str
    carpark_count: int
    total_spaces: int
    avg_occupancy: float
    avg_vacancy: float


class DashboardResponse(BaseModel):
    overview: Dict[str, Any] = {}
    district_ranking: List[DistrictRank] = []
    heatmap_7x24: Dict[str, Any] = {}
    trend_14d: List[Dict[str, Any]] = []


# ============================================================
# 搜尋
# ============================================================
class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]] = []
    count: int = 0


# ============================================================
# AI 對話
# ============================================================
class ChatRequest(BaseModel):
    message: str = Field(..., description="用戶訊息", min_length=1)
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    recommendations: List[Dict[str, Any]] = []
    response_time_ms: float = 0.0


# ============================================================
# 收費
# ============================================================
class FeeInfo(BaseModel):
    park_id: str
    name: str
    district: str
    hourly_fee: Optional[float] = None
    daily_fee: Optional[float] = None
    monthly_fee: Optional[float] = None
    night_fee: Optional[float] = None
    is_government: int = 0
    fee_estimated: int = 0
