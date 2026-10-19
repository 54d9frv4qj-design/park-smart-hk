# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 自然語言查詢解析器
解析港式繁體中文查詢，提取意圖與實體
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from src.config import HK_DISTRICTS
from src.utils.haversine import now_hkt


# 港式用語同義詞映射
SYNONYMS = {
    "泊車": ["泊車", "停車", "泊", "停", "搵位", "搵車位", "泊邊度"],
    "空位": ["空位", "位", "有冇位", "有位", "空", "閒置"],
    "收費": ["收費", "價錢", "價格", "費用", "幾錢", "幾多錢", "點收費", "收幾多"],
    "預測": ["預測", "之後", "一陣", "等下", "遲啲", "未來", "會唔會", "會不會"],
    "咪錶": ["咪錶", "咪表", "路邊", "街邊", "路邊泊車"],
    "夜泊": ["夜泊", "夜晚泊", "過夜", "通宵"],
    "附近": ["附近", "隔離", "隔離", "旁邊", "周圍", "呢頭"],
    "最平": ["最平", "最便宜", "抵", "抵泊", "慳錢"],
    "最易泊": ["最易泊", "最好泊", "最方便", "最多位"],
}

# 地區名稱（含簡稱）
DISTRICT_NAMES = [d["name"] for d in HK_DISTRICTS]
DISTRICT_SHORT = {
    "中環": "中西區", "上環": "中西區", "西環": "中西區", "堅尼地城": "中西區",
    "灣仔": "灣仔區", "銅鑼灣": "灣仔區", "天后": "灣仔區",
    "北角": "東區", "鰂魚涌": "東區", "太古": "東區", "西灣河": "東區", "筲箕灣": "東區", "柴灣": "東區",
    "香港仔": "南區", "鴨脷洲": "南區", "赤柱": "南區", "薄扶林": "南區",
    "尖沙咀": "油尖旺區", "旺角": "油尖旺區", "油麻地": "油尖旺區", "佐敦": "油尖旺區", "大角咀": "油尖旺區",
    "深水埗": "深水埗區", "長沙灣": "深水埗區", "荔枝角": "深水埗區", "石硤尾": "深水埗區",
    "九龍塘": "九龍城區", "九龍城": "九龍城區", "土瓜灣": "九龍城區", "紅磡": "九龍城區", "何文田": "九龍城區",
    "黃大仙": "黃大仙區", "鑽石山": "黃大仙區", "樂富": "黃大仙區",
    "觀塘": "觀塘區", "九龍灣": "觀塘區", "牛頭角": "觀塘區", "秀茂坪": "觀塘區", "藍田": "觀塘區",
    "葵芳": "葵青區", "葵涌": "葵青區", "青衣": "葵青區",
    "荃灣": "荃灣區", "梨木樹": "荃灣區",
    "屯門": "屯門區", "元朗": "元朗區", "天水圍": "元朗區",
    "上水": "北區", "粉嶺": "北區", "沙頭角": "北區",
    "大埔": "大埔區", "太和": "大埔區",
    "沙田": "沙田區", "大圍": "沙田區", "火炭": "沙田區", "馬鞍山": "沙田區",
    "將軍澳": "西貢區", "坑口": "西貢區", "調景嶺": "西貢區", "西貢": "西貢區",
    "東涌": "離島區", "長洲": "離島區", "坪洲": "離島區", "梅窩": "離島區",
}

# 意圖分類
INTENTS = [
    "find_parking",       # 搵位
    "check_fee",          # 查收費
    "predict_vacancy",    # 預測空位
    "find_meter",         # 搵咪錶
    "find_alternative",   # 替代停車場
    "compare_fee",        # 收費比較
    "night_parking",      # 夜泊
    "dashboard_stats",    # 統計數據
    "greeting",           # 問候
    "unknown",            # 未知
]


class QueryParser:
    """自然語言查詢解析器"""

    def __init__(self):
        self.district_pattern = self._build_district_pattern()

    def _build_district_pattern(self) -> re.Pattern:
        """建立地區匹配正則"""
        all_names = list(DISTRICT_NAMES) + list(DISTRICT_SHORT.keys())
        pattern = "|".join(re.escape(name) for name in sorted(all_names, key=len, reverse=True))
        return re.compile(f"({pattern})")

    def parse(self, query: str) -> Dict:
        """
        解析用戶查詢
        :return: {intent, entities, confidence, original_query}
        """
        query = query.strip()
        result = {
            "original_query": query,
            "intent": "unknown",
            "entities": {},
            "confidence": 0.0,
            "parsed_at": now_hkt().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if not query:
            return result

        # 1. 判斷意圖
        intent, confidence = self._classify_intent(query)
        result["intent"] = intent
        result["confidence"] = confidence

        # 2. 提取實體
        result["entities"] = self._extract_entities(query)

        return result

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        """分類查詢意圖"""
        q = query.lower()

        # 問候
        if any(w in q for w in ["你好", "hi", "hello", "早晨", "午安", "晚安"]):
            return "greeting", 0.95

        # 咪錶
        if any(w in q for w in SYNONYMS["咪錶"]):
            return "find_meter", 0.9

        # 夜泊
        if any(w in q for w in SYNONYMS["夜泊"]):
            return "night_parking", 0.85

        # 收費查詢（最平／抵泊先歸入收費，避免被「停車場」誤判為搵位）
        if any(w in q for w in SYNONYMS["最平"] + SYNONYMS["收費"]):
            if "比較" in q or "對比" in q or "最平" in q or "邊個平" in q:
                return "compare_fee", 0.85
            return "check_fee", 0.85

        # 預測
        if any(w in q for w in SYNONYMS["預測"]):
            return "predict_vacancy", 0.85

        # 替代停車場
        if any(w in q for w in ["替代", "第二個", "第二選擇", "其他", "附近"]):
            return "find_alternative", 0.75

        # 統計
        if any(w in q for w in ["統計", "數據", "報告", "全港", "邊區"]):
            return "dashboard_stats", 0.7

        # 最基本：搵位
        if any(w in q for w in SYNONYMS["空位"] + SYNONYMS["泊車"] + SYNONYMS["最易泊"]):
            return "find_parking", 0.8

        return "unknown", 0.3

    def _extract_entities(self, query: str) -> Dict:
        """提取實體：地區、時間、車型、排序偏好"""
        entities = {}

        # 地區
        district_match = self.district_pattern.search(query)
        if district_match:
            raw_name = district_match.group(1)
            entities["district"] = DISTRICT_SHORT.get(raw_name, raw_name)
            entities["district_raw"] = raw_name

        # 時間
        entities["time"] = self._extract_time(query)

        # 車型
        if any(w in query for w in ["電動車", "EV", "充電"]):
            entities["vehicle_type"] = "EV"
        elif any(w in query for w in ["貨車", "van"]):
            entities["vehicle_type"] = "goods"
        elif any(w in query for w in ["電單車", "摩托"]):
            entities["vehicle_type"] = "motorcycle"
        else:
            entities["vehicle_type"] = "privateCar"

        # 排序偏好
        if any(w in query for w in SYNONYMS["最平"]):
            entities["sort_by"] = "fee"
        elif any(w in query for w in SYNONYMS["最易泊"] + SYNONYMS["空位"]):
            entities["sort_by"] = "vacancy"
        elif any(w in query for w in SYNONYMS["附近"]):
            entities["sort_by"] = "distance"
        else:
            entities["sort_by"] = "relevance"

        # 是否需要替代
        entities["need_alternative"] = any(
            w in query for w in ["滿", "爆", "冇位", "無位", "替代", "其他"]
        )

        return entities

    def _extract_time(self, query: str) -> Dict:
        """提取時間實體"""
        now = now_hkt()
        time_info = {"type": "now", "datetime": now}

        # 具體時間
        time_match = re.search(r"(\d{1,2})\s*(?:點|:|：)(\d{0,2})", query)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            if 0 <= hour <= 23:
                target = now.replace(hour=hour, minute=minute, second=0)
                if target < now:
                    target += timedelta(days=1)
                time_info = {"type": "specific", "datetime": target}

        # 相對時間
        elif any(w in query for w in ["一陣", "等下", "遲啲", "快"]):
            time_info = {"type": "soon", "datetime": now + timedelta(minutes=15)}
        elif "30分鐘" in query or "半個鐘" in query:
            time_info = {"type": "30min", "datetime": now + timedelta(minutes=30)}
        elif "60分鐘" in query or "一個鐘" in query or "1個鐘" in query:
            time_info = {"type": "60min", "datetime": now + timedelta(minutes=60)}
        elif "聽日" in query or "聽朝" in query or "明天" in query:
            time_info = {"type": "tomorrow", "datetime": now + timedelta(days=1)}

        return time_info


# 全局解析器實例
_parser = QueryParser()


def parse_query(query: str) -> Dict:
    """便捷函數：解析查詢"""
    return _parser.parse(query)
