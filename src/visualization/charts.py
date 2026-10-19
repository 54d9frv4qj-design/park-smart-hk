# -*- coding: utf-8 -*-
"""統計卡、咪錶收費對比、24 小時空位走勢（Plotly）。"""
from typing import Dict, List
import pandas as pd

from src.config import COLORS
from src.utils.timeutil import hkt_now

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def create_stats_cards(data: Dict) -> List[Dict]:
    return [
        {"label": "停車場總數", "value": f"{int(data.get('total_carparks') or 0):,}",
         "icon": "🅿️", "color": COLORS["primary"], "delta": "全港 18 區"},
        {"label": "總車位", "value": f"{int(data.get('total_spaces') or 0):,}",
         "icon": "🚗", "color": COLORS["accent"], "delta": "私家車位"},
        {"label": "平均佔用率", "value": f"{float(data.get('avg_occupancy') or 0):.0%}",
         "icon": "📊", "color": COLORS["yellow"], "delta": "即時數據"},
        {"label": "路邊咪錶組", "value": int(data.get("total_meters") or 0),
         "icon": "⏱️", "color": COLORS["green"], "delta": "覆蓋全港"},
    ]


def create_meter_vs_carpark_fig(meter_avg_fee: float, carpark_avg_fee: float,
                                title: str = "咪錶 vs 停車場收費對比"):
    if go is None:
        return None
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


def create_24h_vacancy_trend_fig(
    hourly_df: pd.DataFrame,
    current_vacancy: int = 0,
    pred_30min: int = 0,
    pred_60min: int = 0,
    title: str = "24小時空位",
):
    """歷史平均線、今日實時線、30/60 分鐘預測；實時線止於而家。"""
    if go is None or hourly_df is None or hourly_df.empty:
        return None
    try:
        hours = [f"{h:02d}:00" for h in hourly_df["hour"]]
        avg_vals = [float(v) if pd.notna(v) else None for v in hourly_df["avg_vacancy"]]
        today_vals = [float(v) if pd.notna(v) else None for v in hourly_df["today_vacancy"]]

        current_hour = int(hkt_now().strftime("%H"))
        if 0 <= current_hour < len(today_vals) and today_vals[current_hour] is None:
            today_vals[current_hour] = float(current_vacancy)
        for h in range(current_hour + 1, len(today_vals)):
            today_vals[h] = None

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hours, y=avg_vals, mode="lines", name="平均空位",
            line=dict(color="#A0B4C8", width=2, dash="dot"),
            hovertemplate="%{x}<br>平均: %{y:.0f} 個位<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=hours, y=today_vals, mode="lines+markers", name="實時數據",
            line=dict(color=COLORS["primary"], width=3), marker=dict(size=6),
            hovertemplate="%{x}<br>而家: %{y:.0f} 個位<extra></extra>",
        ))

        pred_x = [f"{current_hour:02d}:00", f"{(current_hour + 1) % 24:02d}:00"]
        fig.add_trace(go.Scatter(
            x=pred_x, y=[current_vacancy, pred_60min], mode="lines+markers", name="預測",
            line=dict(color=COLORS["accent"], width=2, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="%{x}<br>預測: %{y:.0f} 個位<extra></extra>",
        ))
        fig.add_annotation(
            x=f"{current_hour:02d}:00", y=current_vacancy,
            text=f"而家: {current_vacancy} 個位",
            showarrow=True, arrowhead=2, arrowsize=1,
            arrowcolor=COLORS["accent"], font=dict(color=COLORS["accent"], size=11),
            ax=0, ay=-40, bgcolor="white", bordercolor=COLORS["accent"], borderwidth=1,
        )
        fig.update_layout(
            title=title, xaxis_title="時間", yaxis_title="空位數量",
            height=350, margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", plot_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F0", rangemode="tozero"),
        )
        return fig
    except Exception as e:
        print(f"create_24h_vacancy_trend_fig 錯誤: {e}")
        return None
