# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 通用圖表組件
統計卡、進度條、佔用率儀表盤、咪錶對比圖
Plotly 為可選依賴，未安裝時相關函數返回 None
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from src.config import COLORS

# 選擇性導入 Plotly
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# 選擇性導入 Matplotlib（降級用）
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _set_chinese_font():
    """設定 Matplotlib 中文字體"""
    if not MATPLOTLIB_AVAILABLE:
        return
    for font_name in ["Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "SimHei"]:
        try:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            break
        except Exception:
            continue


# ============================================================
# 統計卡（純數據，無需圖表庫）
# ============================================================
def create_stats_cards(data: Dict) -> List[Dict]:
    """
    建立統計卡數據

    Args:
        data: 包含 total_carparks, total_spaces, avg_occupancy, green/yellow/red 等

    Returns:
        統計卡列表
    """
    cards = [
        {
            "label": "停車場總數",
            "value": f"{int(data.get('total_carparks') or 0):,}",
            "icon": "🅿️",
            "color": COLORS["primary"],
            "delta": "全港 18 區",
        },
        {
            "label": "總車位",
            "value": f"{int(data.get('total_spaces') or 0):,}",
            "icon": "🚗",
            "color": COLORS["accent"],
            "delta": "私家車位",
        },
        {
            "label": "平均佔用率",
            "value": f"{float(data.get('avg_occupancy') or 0):.0%}",
            "icon": "📊",
            "color": COLORS["yellow"],
            "delta": "即時數據",
        },
        {
            "label": "路邊咪錶組",
            "value": int(data.get("total_meters") or 0),
            "icon": "⏱️",
            "color": COLORS["green"],
            "delta": "覆蓋全港",
        },
    ]
    return cards


def create_status_distribution(data: Dict) -> List[Dict]:
    """建立狀態分佈數據"""
    return [
        {"status": "充足", "count": data.get("green_count", 0), "color": COLORS["green"]},
        {"status": "偏緊", "count": data.get("yellow_count", 0), "color": COLORS["yellow"]},
        {"status": "緊張", "count": data.get("red_count", 0), "color": COLORS["red"]},
    ]


# ============================================================
# 佔用率儀表盤
# ============================================================
def create_occupancy_gauge(
    occupancy_rate: float,
    title: str = "即時佔用率",
):
    """
    建立佔用率儀表盤

    Args:
        occupancy_rate: 佔用率 0-1
        title: 標題

    Returns:
        Plotly Figure 或 Matplotlib Figure
    """
    if PLOTLY_AVAILABLE:
        color = (COLORS["green"] if occupancy_rate < 0.5
                 else COLORS["yellow"] if occupancy_rate < 0.7
                 else COLORS["red"])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=occupancy_rate * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 50], "color": "rgba(46, 204, 113, 0.2)"},
                    {"range": [50, 70], "color": "rgba(241, 196, 15, 0.2)"},
                    {"range": [70, 100], "color": "rgba(231, 76, 60, 0.2)"},
                ],
            },
        ))
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(4, 3), subplot_kw={"projection": "polar"})
        theta = np.linspace(np.pi, 0, 100)
        r = np.ones_like(theta)
        ax.plot(theta, r, color="#ddd", linewidth=10)
        # 指針
        pointer_theta = np.pi * (1 - occupancy_rate)
        ax.plot([pointer_theta, pointer_theta], [0, 1], color="#E74C3C", linewidth=3)
        ax.set_ylim(0, 1.2)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.set_title(f"{title}: {occupancy_rate:.0%}", pad=20)
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 24 小時歷史走勢圖
# ============================================================
def create_history_chart(
    df: pd.DataFrame,
    time_col: str = "snapshot_time",
    value_col: str = "vacancy",
    title: str = "24 小時空位走勢",
):
    """建立歷史走勢圖"""
    if df is None or df.empty:
        return None

    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df[time_col], y=df[value_col],
            mode="lines", name="空位",
            line=dict(color=COLORS["accent"], width=2),
            fill="tozeroy", fillcolor="rgba(0, 168, 181, 0.1)",
        ))
        fig.update_layout(
            title=title, xaxis_title="時間", yaxis_title="空位數",
            height=300, margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(df[time_col], df[value_col], color="#00A8B5", linewidth=2)
        ax.fill_between(df[time_col], df[value_col], alpha=0.1, color="#00A8B5")
        ax.set_xlabel("時間")
        ax.set_ylabel("空位數")
        ax.set_title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 預測走勢圖
# ============================================================
def create_forecast_chart(
    history_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    time_col: str = "time",
    value_col: str = "vacancy",
    title: str = "空位預測",
):
    """建立歷史+預測走勢圖"""
    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        if history_df is not None and not history_df.empty:
            fig.add_trace(go.Scatter(
                x=history_df[time_col], y=history_df[value_col],
                mode="lines", name="歷史",
                line=dict(color=COLORS["primary"], width=2),
            ))
        if forecast_df is not None and not forecast_df.empty:
            fig.add_trace(go.Scatter(
                x=forecast_df[time_col], y=forecast_df[value_col],
                mode="lines+markers", name="預測",
                line=dict(color=COLORS["accent"], width=2, dash="dash"),
            ))
        fig.update_layout(
            title=title, xaxis_title="時間", yaxis_title="空位數",
            height=300, margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 3.5))
        if history_df is not None and not history_df.empty:
            ax.plot(history_df[time_col], history_df[value_col],
                    color="#1B3A5C", linewidth=2, label="歷史")
        if forecast_df is not None and not forecast_df.empty:
            ax.plot(forecast_df[time_col], forecast_df[value_col],
                    color="#00A8B5", linewidth=2, linestyle="--", marker="o", label="預測")
        ax.set_xlabel("時間")
        ax.set_ylabel("空位數")
        ax.set_title(title)
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 咪錶 vs 停車場對比圖
# ============================================================
def create_meter_comparison_fig(
    meter_avg_fee: float,
    carpark_avg_fee: float,
    title: str = "咪錶 vs 停車場收費對比",
):
    """建立咪錶與停車場收費對比圖"""
    if PLOTLY_AVAILABLE:
        fig = go.Figure(go.Bar(
            x=["路邊咪錶", "停車場"],
            y=[meter_avg_fee, carpark_avg_fee],
            marker_color=[COLORS["accent"], COLORS["primary"]],
            text=[f"HK${meter_avg_fee}", f"HK${carpark_avg_fee}"],
            textposition="outside",
        ))
        fig.update_layout(
            title=title, yaxis_title="平均時租 (HKD)",
            height=300, margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(5, 3.5))
        bars = ax.bar(["路邊咪錶", "停車場"], [meter_avg_fee, carpark_avg_fee],
                      color=["#00A8B5", "#1B3A5C"])
        ax.set_ylabel("平均時租 (HKD)")
        ax.set_title(title)
        for bar, val in zip(bars, [meter_avg_fee, carpark_avg_fee]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"HK${val}", ha="center")
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 別名（相容舊代碼）
# ============================================================
create_meter_vs_carpark_fig = create_meter_comparison_fig
