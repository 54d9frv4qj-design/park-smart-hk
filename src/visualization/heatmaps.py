# -*- coding: utf-8 -*-
"""地區排名條形圖與各地區收費箱形圖（Plotly）。"""
import pandas as pd

from src.config import COLORS

try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def create_district_ranking_fig(
    df: pd.DataFrame,
    value_col: str = "occupancy_rate",
    name_col: str = "district",
    title: str = "地區排名",
    ascending: bool = True,
    top_n: int = 18,
):
    if go is None or df is None or df.empty:
        return None
    d = df.sort_values(value_col, ascending=ascending).head(top_n)
    colors = [
        COLORS["green"] if v < 0.5 else COLORS["yellow"] if v < 0.7 else COLORS["red"]
        for v in d[value_col]
    ]
    fig = go.Figure(go.Bar(
        x=d[value_col], y=d[name_col], orientation="h",
        marker_color=colors,
        text=[f"{v:.0%}" for v in d[value_col]],
        textposition="outside",
    ))
    fig.update_layout(
        title=title, xaxis_title="佔用率",
        height=max(300, top_n * 25),
        margin=dict(l=10, r=60, t=40, b=10),
        xaxis=dict(tickformat=".0%"),
    )
    return fig


def create_district_fee_fig(df: pd.DataFrame, title: str = "各地區時租分佈（箱形圖）"):
    """垂直箱形圖：每區中位數、四分位同最低~最高。"""
    if go is None or df is None or df.empty:
        return None
    d = df[["district", "hourly_fee"]].dropna()
    d = d[d["hourly_fee"] > 0]
    if d.empty:
        return None
    order = d.groupby("district")["hourly_fee"].median().sort_values().index.tolist()
    fig = go.Figure()
    for name in order:
        vals = d.loc[d["district"] == name, "hourly_fee"]
        fig.add_trace(go.Box(
            x=[name] * len(vals), y=vals, name=name,
            boxpoints=False,
            marker_color=COLORS["primary"],
            line=dict(color=COLORS["primary"]),
            hovertemplate=f"{name}<br>時租 $%{{y:.0f}}<extra></extra>",
        ))
    fig.update_layout(
        title=title, xaxis_title="地區", yaxis_title="時租 HKD",
        height=400, showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
