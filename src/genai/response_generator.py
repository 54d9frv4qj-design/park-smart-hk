# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 港式繁體中文回應生成器
規則式回應 + 可選 LLM 增強
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import urllib.request
import urllib.error
import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, GENAI_LANGUAGE, GENAI_TEMPERATURE, GENAI_MAX_TOKENS
from src.utils.haversine import now_hkt, status_label
from src.utils.logger import log


def _fee_text(v) -> str:
    """NaN / 0 / 缺失 → 「—」，否則 HK$ 整數金額"""
    if v is None or (isinstance(v, float) and pd.isna(v)) or float(v) <= 0:
        return "—"
    return f"HK${float(v):.0f}"


LAST_LLM_ERROR = None


class ResponseGenerator:
    """港式繁體中文回應生成器"""

    def __init__(self, use_llm: bool = None):
        self.use_llm = use_llm if use_llm is not None else bool(OPENAI_API_KEY)
        self.llm_client = None

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

        llm_intents = {"find_parking", "check_fee"}
        if self.use_llm and intent in llm_intents:
            llm_reply = self._generate_llm(intent, entities, recommendations, context)
            if llm_reply:
                return llm_reply
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

            # 處理空值同 NaN（0/缺失都當未知，唔顯示 HK$0）
            if vacancy is None or (isinstance(vacancy, float) and pd.isna(vacancy)):
                vac_text = "—"
            else:
                vac_text = str(int(vacancy))
            if total is None or (isinstance(total, float) and pd.isna(total)):
                total_text = "—"
            else:
                total_text = str(int(total)) if isinstance(total, (int, float)) else str(total)
            if fee is None or (isinstance(fee, float) and pd.isna(fee)) or float(fee) <= 0:
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

        def _fee(v):
            if v is None or (isinstance(v, float) and pd.isna(v)) or float(v) <= 0:
                return "—"
            return f"HK${float(v):.0f}"

        lines = [f"「{district}」停車場收費：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            hourly = _fee(cp.get("hourly_fee"))
            daily = _fee(cp.get("daily_fee"))
            monthly = _fee(cp.get("monthly_fee"))
            gov = "（政府場）" if cp.get("is_government") else ""
            lines.append(
                f"{i}. **{name}**{gov}\n"
                f"   時租 {hourly}｜日租 {daily}｜月票 {monthly}"
            )

        priced = [c for c in recommendations if isinstance(c.get("hourly_fee"), (int, float)) and c["hourly_fee"] > 0]
        if priced:
            cheapest = min(priced, key=lambda x: x["hourly_fee"])
            lines.append(f"\n💰 最平係 **{cheapest['name']}**，時租 HK${cheapest['hourly_fee']:.0f}！")
        return "\n".join(lines)

    def _predict_response(
        self, district: str, recommendations: List[Dict], context: Dict
    ) -> str:
        lines = []
        area = f"「{district}」" if district else "呢度"

        if recommendations:
            lines.append(f"{area}空位預測：\n")
            for i, cp in enumerate(recommendations[:3], 1):
                current = cp.get("vacancy")
                current_val = None
                if current is not None and not (isinstance(current, float) and pd.isna(current)):
                    current_val = int(current)
                pred_30 = cp.get("prediction_30min")
                pred_60 = cp.get("prediction_60min")
                if pred_30 is None or (isinstance(pred_30, float) and pd.isna(pred_30)):
                    pred_30 = max(0, current_val - 2) if current_val is not None else "—"
                if pred_60 is None or (isinstance(pred_60, float) and pd.isna(pred_60)):
                    pred_60 = max(0, current_val - 4) if current_val is not None else "—"

                total = cp.get("total_spaces")
                total_text = "—"
                if total is not None and not (isinstance(total, float) and pd.isna(total)):
                    total_text = str(int(total))

                lines.append(f"{i}. **{cp.get('name', '')}**")
                lines.append(f"   而家：{current_val if current_val is not None else '—'}/{total_text}；30分鐘後約 {pred_30}；60分鐘後約 {pred_60}")
                if isinstance(pred_30, (int, float)) and isinstance(total, (int, float)) and total > 0:
                    occupancy_30 = 1 - pred_30 / total
                    if occupancy_30 >= 0.95:
                        lines.append("   🔴 好大機會滿座")
                    elif occupancy_30 >= 0.8:
                        lines.append("   🟡 會比較緊張")
                    else:
                        lines.append("   🟢 應該仲有位")
                lines.append("")
        else:
            lines.append(f"唔好意思，{area}暫時無合適預測數據。")

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
            # 轉換 float 為 int（如 1.0 → 1）
            if isinstance(vacant, float) and vacant.is_integer():
                vacant = int(vacant)
            if isinstance(total, float) and total.is_integer():
                total = int(total)
            if isinstance(fee, float) and fee.is_integer():
                fee = int(fee)
            lines.append(
                f"{i}. **{street}**\n"
                f"   空位：{vacant}/{total}｜時租 {_fee_text(fee)}｜最長 {max_dur} 分鐘"
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
            if isinstance(vacancy, (int, float)) and not pd.isna(vacancy):
                vacancy = int(vacancy)
            dist = cp.get("distance_km", "?")
            fee = cp.get("hourly_fee", "?")
            walk = cp.get("walking_minutes", "?")
            lines.append(
                f"{i}. **{name}**（{dist}km，步行約{walk}分鐘）\n"
                f"   空位：{vacancy}｜時租：{_fee_text(fee)}"
            )
        return "\n".join(lines)

    def _compare_fee_response(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return "暫時無收費比較數據。"

        lines = ["收費比較（由平到貴）：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            hourly = _fee_text(cp.get("hourly_fee"))
            daily = _fee_text(cp.get("daily_fee"))
            lines.append(f"{i}. {name}：時租 {hourly}，日租 {daily}")
        return "\n".join(lines)

    def _night_parking_response(self, district: str, recommendations: List[Dict]) -> str:
        if not recommendations:
            return f"「{district}」附近搵唔到夜泊停車場。"

        lines = [f"「{district}」夜泊選擇：\n"]
        for i, cp in enumerate(recommendations[:5], 1):
            name = cp.get("name", "未知")
            night_fee = _fee_text(cp.get("night_fee"))
            hourly = _fee_text(cp.get("hourly_fee"))
            lines.append(f"{i}. **{name}**：夜泊 {night_fee}（時租 {hourly}）")
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
                "你係泊得好 Park Smart HK，香港停車場助手。"
                "用港式繁體中文簡潔回答。只能使用下方推薦結果，不得自創停車場、空位或收費。"
                "金額寫 HK$，空位同車位數目照原樣，冇資料就寫「—」。"
            )

            user_prompt = (
                f"用戶查詢意圖：{intent}\n"
                f"提取實體：{entities}\n"
                f"推薦結果：{recommendations[:3]}\n"
                f"上下文：{context}\n\n"
                "按推薦結果直接回答，先講最適合嘅選擇。"
            )

            payload = {
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": GENAI_TEMPERATURE,
                "max_tokens": GENAI_MAX_TOKENS,
            }
            req = urllib.request.Request(
                f"{OPENAI_BASE_URL}/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.load(resp)
            content = data["choices"][0]["message"].get("content")
            if content:
                log.info("LLM 回應成功")
            return content.strip() if content else None
        except Exception as e:
            global LAST_LLM_ERROR
            LAST_LLM_ERROR = str(e)
            log.warning(f"LLM 生成失敗，改用規則式：{e}")
            return None


# 全局生成器實例
_generator = ResponseGenerator()


def generate_response(
    intent: str,
    entities: Dict,
    recommendations: List[Dict],
    context: Dict = None,
) -> str:
    """便捷函數：生成回應"""
    return _generator.generate(intent, entities, recommendations, context or {})
