# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 即時空位（App 端直接打政府 API 覆蓋 DB 快照）

Streamlit Cloud 嘅 DB 係部署時從 CSV 重建、之後唔會自己更新；
呢個模組喺頁面渲染時直接打政府空位 API，攞最新空位覆蓋上去，
令「實時空位」唔受部署時間凍結影響。失敗時返回空 dict，頁面降級用 DB 舊值。
"""
from src.data_fetch.carpark_api import fetch_realtime_vacancy, parse_vacancy


def fetch_live_vacancy_map() -> dict:
    """
    返回 {park_id(str): {"vacancy": int, "vacancy_ev": int, "update": str}}
    網絡/解析失敗返回空 dict（唔拋例外，避免令整個頁面崩）。
    """
    out: dict = {}
    try:
        raw_list = fetch_realtime_vacancy()
    except Exception:
        return out
    for raw in raw_list:
        p = parse_vacancy(raw)
        if not p:
            continue
        out[p["park_id"]] = {
            "vacancy": p["vacancy"],
            "vacancy_ev": p.get("vacancy_ev", 0),
            "update": p.get("snapshot_time", ""),
        }
    return out
