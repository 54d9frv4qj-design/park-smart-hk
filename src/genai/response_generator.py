# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 港式繁體中文回應生成器
規則式回應 + 可選 LLM 增強
"""
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, GENAI_LANGUAGE, GENAI_TEMPERATURE, GENAI_MAX_TOKENS
from src.utils.haversine import now_hkt, status_label
from src.utils.logger import log


class ResponseGenerator:
    """港式繁體中文回應生成器"""

    def __init__(self, use_llm: bool = None):
        self.use_llm = use_llm if use_llm is not None else bool(OPENAI_API_KEY)
        self.llm_client = None
        if self.use_llm:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url=OPENAI_BASE_URL,
                )
            except Exception as e:
                log.warning(f"LLM 客戶端初始化失敗，降級為規則式：{e}")
                self.use_llm = False

    def generate(
        self,
        intent: str,
        entities: Dict,
        recommendations: List[Dict],
        context: Dict = None,
    ) -> str:
        """
        生成回應
        :param intent: 解析出的意圖
        :param entities: 提取的實體
        :param recommendations: 推薦結果
        :param context: 額外上下文（天氣、統計等）
        """
        context = context or {}

        if self.use_llm and self.llm_client:
            return self._generate_llm(intent, entities, recommendations, context)
        return self._generate_rule_based(intent, entities, recommendations, context)

    def _generate_rule_based(
        self, intent: str, entities: Dict,
        recommendations: List[Dict], context: Dict,
    ) -> str:
        """規則式回應（港式用語）"""
        district = entities.get("district", "")
        district_raw = entities.get("district_raw", district)

        if intent == "greeting":
            return self._greeting_response()

        if intent == "find_parking":
            return self._find_parking_response(district_raw, recommendations)

        if intent == "check_fee":
            return self._fee_response(district_raw, recommendations)

        if intent == "predict_vacancy":
            return self._predict_response(district_raw, recommendations, context)

        if intent == "find_meter":
            return self._meter_response(district_raw, recommendations)

        if intent == "find_alternative":
            return self._alternative_response(recommendations)

        if intent == "compare_fee":
            return self._compare_fee_response(recommendations)

        if intent == "night_parking":
            return self._night_parking_response(district_raw, recommendations)

        if intent == "dashboard_stats":
            return self._stats_response(context)

        return self._fallback_response()

    def _greeting_response(self) -> str:
        return (
            "你好！我係泊得好 Park Smart HK 🅿️\n\n"
            "我可以幫你：\n"
            "• 搵邊度有位泊（「旺角而家邊度有位？」）\n"
            "• 查停車場收費（「中環邊個停車場最平？」）\n"
            "• 預測未來空位（「30分鐘後銅鑼灣會唔會滿？」）\n"
            "• 搵路邊咪錶（「附近有冇咪錶？」）\n"
            "• 比較收費（「尖沙咀停車場收費比較」）\n\n"
            "想搵邊度泊車？話我知就得！"
        )

    def _find_parking_response(self, district: str, recommendations: List[Dict]) -> str:
        if not recommendations:
            area = f"「{district}」" if district else "而家"
            return f"唔好意思，{area}搵唔到合適嘅停車場。試下講近啲嘅地區？"

        lines = []
        area = f"「{district}」" if district else "附近"
        lines.append(f"{area}最易泊嘅停車場：\n")

        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            vacancy = cp.get("vacancy")
            total = cp.get("total_spaces", "?")
            fee = cp.get("hourly_fee")
            status = status_label(cp.get("status", "unknown"))
            reason = cp.get("recommendation_reason", "")
            dist = cp.get("distance_km", "")

            # 處理空值同 NaN
            if vacancy is None or (isinstance(vacancy, float) and pd.isna(vacancy)):
                vac_text = "—"
            else:
                vac_text = str(int(vacancy))
            if total is None or (isinstance(total, float) and pd.isna(total)):
                total_text = "—"
            else:
                total_text = str(int(total)) if isinstance(total, (int, float)) else str(total)
            if fee is None or (isinstance(fee, float) and pd.isna(fee)):
                fee_text = "查詢中"
            else:
                fee_text = f"HK${float(fee):.0f}"

            dist_text = f"（{dist}km）" if dist else ""
            lines.append(
                f"{i}. **{name}**{dist_text}\n"
                f"   空位：{vac_text}/{total_text}（{status}）｜時租：{fee_text}\n"
                f"   {reason}"
            )

        lines.append(f"\n💡 建議你去第 1 個，空位充足又就腳！")
        return "\n".join(lines)

    def _fee_response(self, district: str, recommendations: List[Dict]) -> str:
        if not recommendations:
            return f"唔好意思，「{district}」暫時搵唔到收費資料。"

        lines = [f"「{district}」停車場收費：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            hourly = cp.get("hourly_fee", "?")
            daily = cp.get("daily_fee", "?")
            monthly = cp.get("monthly_fee", "?")
            gov = "（政府場）" if cp.get("is_government") else ""
            lines.append(
                f"{i}. **{name}**{gov}\n"
                f"   時租 HK${hourly}｜日租 HK${daily}｜月票 HK${monthly}"
            )

        cheapest = min(recommendations, key=lambda x: x.get("hourly_fee", 999))
        lines.append(f"\n💰 最平係 **{cheapest['name']}**，時租 HK${cheapest.get('hourly_fee', '?')}！")
        return "\n".join(lines)

    def _predict_response(
        self, district: str, recommendations: List[Dict], context: Dict
    ) -> str:
        lines = []
        area = f"「{district}」" if district else "呢度"

        if recommendations:
            cp = recommendations[0]
            pred_30 = cp.get("prediction_30min", "?")
            pred_60 = cp.get("prediction_60min", "?")
            current = cp.get("vacancy", "?")

            lines.append(f"**{cp.get('name', '')}** 空位預測：\n")
            lines.append(f"• 而家：{current} 個位")
            lines.append(f"• 30分鐘後：預測 {pred_30} 個位")
            lines.append(f"• 60分鐘後：預測 {pred_60} 個位")

            if isinstance(pred_30, (int, float)) and isinstance(current, (int, float)):
                if pred_30 > current:
                    lines.append("\n📈 空位會增加，遲少少去可能更易泊！")
                elif pred_30 < current:
                    lines.append("\n📉 空位會減少，建議你而家就去！")
                else:
                    lines.append("\n➡️ 空位大致維持不變。")
        else:
            lines.append(f"唔好意思，{area}暫時無預測數據。")

        return "\n".join(lines)

    def _meter_response(self, district: str, recommendations: List[Dict]) -> str:
        if not recommendations:
            return f"「{district}」附近暫時搵唔到路邊咪錶，試下停車場？"

        lines = [f"「{district}」附近路邊咪錶：\n"]
        for i, mt in enumerate(recommendations[:5], 1):
            street = mt.get("street_name", "未知街道")
            vacant = mt.get("vacant_spaces", "?")
            total = mt.get("total_spaces", "?")
            fee = mt.get("hourly_fee", "?")
            max_dur = mt.get("max_duration", 120)
            lines.append(
                f"{i}. **{street}**\n"
                f"   空位：{vacant}/{total}｜時租 HK${fee}｜最長 {max_dur} 分鐘"
            )

        lines.append("\n⚠️ 咪錶通常有時間限制，記住睇清楚牌面！")
        return "\n".join(lines)

    def _alternative_response(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return "附近搵唔到替代停車場，建議你擴大搜尋範圍。"

        lines = ["附近替代停車場：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            vacancy = cp.get("vacancy", "?")
            dist = cp.get("distance_km", "?")
            fee = cp.get("hourly_fee", "?")
            walk = cp.get("walking_minutes", "?")
            lines.append(
                f"{i}. **{name}**（{dist}km，步行約{walk}分鐘）\n"
                f"   空位：{vacancy}｜時租：HK${fee}"
            )
        return "\n".join(lines)

    def _compare_fee_response(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return "暫時無收費比較數據。"

        lines = ["收費比較（由平到貴）：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            hourly = cp.get("hourly_fee", "?")
            daily = cp.get("daily_fee", "?")
            lines.append(f"{i}. {name}：時租 HK${hourly}，日租 HK${daily}")
        return "\n".join(lines)

    def _night_parking_response(self, district: str, recommendations: List[Dict]) -> str:
        if not recommendations:
            return f"「{district}」附近搵唔到夜泊停車場。"

        lines = [f"「{district}」夜泊選擇：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            night_fee = cp.get("night_fee", "?")
            hourly = cp.get("hourly_fee", "?")
            lines.append(f"{i}. **{name}**：夜泊 HK${night_fee}（時租 HK${hourly}）")
        lines.append("\n🌙 夜泊通常 8PM 開始，記住確認返時間！")
        return "\n".join(lines)

    def _stats_response(self, context: Dict) -> str:
        total = context.get("total_carparks", "?")
        avg_occ = context.get("avg_occupancy", 0)
        green = context.get("green_count", "?")
        yellow = context.get("yellow_count", "?")
        red = context.get("red_count", "?")

        return (
            f"📊 全港停車場統計：\n\n"
            f"• 停車場總數：{total}\n"
            f"• 平均佔用率：{avg_occ:.1%}\n"
            f"• 充足（綠）：{green}\n"
            f"• 偏緊（黃）：{yellow}\n"
            f"• 滿座（紅）：{red}\n\n"
            f"💡 而家全港平均 {avg_occ:.0%} 滿，想泊車就趁早！"
        )

    def _fallback_response(self) -> str:
        return (
            "唔好意思，我唔係好明你想問咩 🤔\n\n"
            "你可以試下問：\n"
            "• 「旺角而家邊度有位泊？」\n"
            "• 「中環停車場收費幾多？」\n"
            "• 「30分鐘後銅鑼灣會唔會滿？」\n"
            "• 「附近有冇路邊咪錶？」"
        )

    def _generate_llm(
        self, intent: str, entities: Dict,
        recommendations: List[Dict], context: Dict,
    ) -> str:
        """使用 LLM 生成更自然的回應"""
        try:
            # 構建提示
            system_prompt = (
                "你係泊得好 Park Smart HK，一個香港停車場推薦助手。"
                "請用港式繁體中文回答，用語自然貼地，"
                "可以用「嘅」「咗」「喺」「哋」等港式用語。"
                "回答要簡潔直接，包含具體數據。"
            )

            user_prompt = (
                f"用戶查詢意圖：{intent}\n"
                f"提取實體：{entities}\n"
                f"推薦結果：{recommendations[:3]}\n"
                f"上下文：{context}\n\n"
                f"請生成一個港式繁體中文回應，直接回答用戶問題。"
            )

            response = self.llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            return response.choices[0].message.content
        except Exception as e:
            # LLM 失敗時降級為規則式
            return self._generate_rule_based(intent, entities, recommendations, context)


# 全局生成器實例
_generator = ResponseGenerator()


def generate_response(intent: str, entities: Dict, recommendations: List[Dict], **kwargs) -> str:
    """便捷函數：生成回應"""
    return _generator.generate(intent, entities, recommendations, **kwargs)
