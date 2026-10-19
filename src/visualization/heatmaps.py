# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 熱力圖組件
7×24 時段熱力圖、地區排名、14天趨勢
優先使用 Plotly，未安裝時降級為 Matplotlib
"""
from typing import Optional
import pandas as pd
import numpy as np

from src.config import COLORS
from src.utils.logger import log

# 選擇性導入 Plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# 選擇性導入 Matplotlib（降級用）
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _set_chinese_font():
    """設定 Matplotlib 中文字體"""
    if not MATPLOTLIB_AVAILABLE:
        return
    # 嘗試設定繁體中文字體
    for font_name in ["Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "SimHei"]:
        try:
            plt.rcParams["font.sans-serif"] = [font_name]
            plt.rcParams["axes.unicode_minus"] = False
            break
        except Exception:
            continue


# ============================================================
# 7×24 時段熱力圖
# ============================================================
def create_7x24_heatmap_fig(
    pivot_df: pd.DataFrame,
    title: str = "7×24 時段繁忙熱力圖",
):
    """
    建立 7×24 時段熱力圖

    Args:
        pivot_df: DataFrame，index=星期(0-6)，columns=小時(0-23)，values=佔用率
        title: 圖表標題

    Returns:
        Plotly Figure 或 Matplotlib Figure
    """
    if pivot_df is None or pivot_df.empty:
        return None

    if PLOTLY_AVAILABLE:
        try:
            # 將所有數據轉換成純 Python 類型，避免 pandas/numpy 類型導致 Plotly 內部錯誤
            z_values = []
            for row in pivot_df.values.tolist():
                z_values.append([float(v) if v is not None and pd.notna(v) else 0.0 for v in row])
            x_labels = [str(h) + "時" for h in list(pivot_df.columns)]
            y_labels = [str(idx) for idx in list(pivot_df.index)]

            fig = go.Figure(data=go.Heatmap(
                z=z_values,
                x=x_labels,
                y=y_labels,
                colorscale=[
                    [0.0, "#2ECC71"],
                    [0.5, "#F1C40F"],
                    [1.0, "#E74C3C"],
                ],
                zmin=0.0, zmax=1.0,
                hovertemplate="%{y} %{x}<br>佔用率: %{z:.0%}<extra></extra>",
            ))
            fig.update_layout(
                title=title,
                xaxis_title="小時",
                yaxis_title="星期",
                height=400,
                margin=dict(l=10, r=10, t=40, b=10),
            )
            return fig
        except Exception as e:
            log.warning(f"Plotly 熱力圖失敗，降級 Matplotlib: {e}")

    if MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(12, 4))
        z_data = [[float(v) if v is not None and pd.notna(v) else 0.0 for v in row]
                  for row in pivot_df.values.tolist()]
        im = ax.imshow(z_data, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(min(24, len(pivot_df.columns))))
        ax.set_xticklabels([str(h) for h in list(pivot_df.columns)[:24]], fontsize=8)
        day_names = ["日", "一", "二", "三", "四", "五", "六"]
        n_rows = min(7, len(pivot_df))
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels(day_names[:n_rows])
        ax.set_xlabel("小時")
        ax.set_ylabel("星期")
        ax.set_title(title)
        plt.colorbar(im, ax=ax, label="佔用率")
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 地區排名條形圖
# ============================================================
def create_district_ranking_fig(
    df: pd.DataFrame,
    value_col: str = "occupancy_rate",
    name_col: str = "district",
    title: str = "地區排名",
    ascending: bool = True,
    top_n: int = 18,
):
    """
    建立地區排名條形圖

    Args:
        df: DataFrame
        value_col: 數值欄位
        name_col: 名稱欄位
        title: 標題
        ascending: 是否升序（True=由低到高）
        top_n: 顯示前 N 個

    Returns:
        Figure
    """
    if df is None or df.empty:
        return None

    df_sorted = df.sort_values(value_col, ascending=ascending).head(top_n)

    if PLOTLY_AVAILABLE:
        colors = [COLORS["green"] if v < 0.5 else COLORS["yellow"] if v < 0.7 else COLORS["red"]
                  for v in df_sorted[value_col]]
        fig = go.Figure(go.Bar(
            x=df_sorted[value_col],
            y=df_sorted[name_col],
            orientation="h",
            marker_color=colors,
            text=[f"{v:.0%}" for v in df_sorted[value_col]],
            textposition="outside",
        ))
        fig.update_layout(
            title=title,
            xaxis_title="佔用率",
            height=max(300, top_n * 25),
            margin=dict(l=10, r=60, t=40, b=10),
            xaxis=dict(tickformat=".0%"),
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(8, max(4, top_n * 0.3)))
        colors = ["#2ECC71" if v < 0.5 else "#F1C40F" if v < 0.7 else "#E74C3C"
                  for v in df_sorted[value_col]]
        bars = ax.barh(df_sorted[name_col], df_sorted[value_col], color=colors)
        ax.set_xlabel("佔用率")
        ax.set_title(title)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
        for bar, val in zip(bars, df_sorted[value_col]):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:.0%}", va="center", fontsize=8)
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 14 天趨勢折線圖
# ============================================================
def create_trend_fig(
    df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "occupancy_rate",
    title: str = "14 天趨勢",
    x_col: str = None,
    y_col: str = None,
):
    """
    建立趨勢折線圖

    Args:
        df: DataFrame
        date_col: 日期欄位（或用 x_col）
        value_col: 數值欄位（或用 y_col）
        title: 標題
        x_col: 別名，等同 date_col
        y_col: 別名，等同 value_col

    Returns:
        Figure
    """
    if df is None or df.empty:
        return None

    # 相容兩種參數命名
    if x_col:
        date_col = x_col
    if y_col:
        value_col = y_col

    # 確保欄位存在
    if date_col not in df.columns or value_col not in df.columns:
        log.warning(f"create_trend_fig: 欄位唔存在 ({date_col}, {value_col}), 可用: {list(df.columns)}")
        return None

    if PLOTLY_AVAILABLE:
        try:
            # 轉換為純 Python 類型避免 Plotly 內部錯誤
            x_vals = [str(v) for v in df[date_col].tolist()]
            y_vals = [float(v) if v is not None and pd.notna(v) else 0.0 for v in df[value_col].tolist()]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name="平均佔用率",
                line=dict(color="#00A8B5", width=2),
                fill="tozeroy",
                fillcolor="rgba(0, 168, 181, 0.1)",
            ))
            fig.update_layout(
                title=title,
                xaxis_title="日期",
                yaxis_title="佔用率",
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
                yaxis=dict(tickformat=".0%"),
            )
            return fig
        except Exception as e:
            log.warning(f"Plotly 趨勢圖失敗，降級 Matplotlib: {e}")

    if MATPLOTLIB_AVAILABLE:
        try:
            _set_chinese_font()
            fig, ax = plt.subplots(figsize=(10, 4))
            y_vals = [float(v) if v is not None and pd.notna(v) else 0.0 for v in df[value_col].tolist()]
            ax.plot(range(len(df)), y_vals, color="#00A8B5", linewidth=2, marker="o", markersize=4)
            ax.fill_between(range(len(df)), y_vals, alpha=0.1, color="#00A8B5")
            ax.set_xlabel("日期")
            ax.set_ylabel("佔用率")
            ax.set_title(title)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
            plt.xticks(rotation=45)
            plt.tight_layout()
            return fig
        except Exception as e:
            log.warning(f"Matplotlib 趨勢圖失敗: {e}")

    return None


# ============================================================
# 收費比較柱狀圖
# ============================================================
def create_fee_comparison_fig(
    df: pd.DataFrame,
    name_col: str = "name",
    fee_col: str = "hourly_fee",
    title: str = "停車場收費比較",
    top_n: int = 20,
):
    """
    建立收費比較柱狀圖

    Args:
        df: DataFrame
        name_col: 名稱欄位
        fee_col: 收費欄位
        title: 標題
        top_n: 顯示前 N 個

    Returns:
        Figure
    """
    if df is None or df.empty:
        return None

    df_sorted = df.sort_values(fee_col, ascending=True).head(top_n)

    if PLOTLY_AVAILABLE:
        fig = go.Figure(go.Bar(
            x=df_sorted[name_col],
            y=df_sorted[fee_col],
            marker_color=COLORS["primary"],
            text=[f"HK${v}" for v in df_sorted[fee_col]],
            textposition="outside",
        ))
        fig.update_layout(
            title=title,
            xaxis_title="停車場",
            yaxis_title="時租 (HKD)",
            height=400,
            margin=dict(l=10, r=10, t=40, b=80),
            xaxis_tickangle=-45,
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar(df_sorted[name_col], df_sorted[fee_col], color="#1B3A5C")
        ax.set_xlabel("停車場")
        ax.set_ylabel("時租 (HKD)")
        ax.set_title(title)
        plt.xticks(rotation=45, ha="right", fontsize=8)
        for i, v in enumerate(df_sorted[fee_col]):
            ax.text(i, v + 0.5, f"${v}", ha="center", fontsize=7)
        plt.tight_layout()
        return fig

    return None


# ============================================================
# 模型表現比較圖
# ============================================================
def create_model_performance_fig(
    results_df: pd.DataFrame,
    model_col: str = "model_name",
    metric_col: str = "mae",
    title: str = "模型表現比較（MAE 越低越好）",
):
    """
    建立模型表現比較柱狀圖

    Args:
        results_df: 模型評估結果 DataFrame
        model_col: 模型名稱欄位
        metric_col: 指標欄位（mae / rmse / mape）
        title: 標題

    Returns:
        Figure
    """
    if results_df is None or results_df.empty:
        return None

    df_sorted = results_df.sort_values(metric_col, ascending=True)

    if PLOTLY_AVAILABLE:
        colors = [COLORS["green"] if i == 0 else COLORS["primary"]
                  for i in range(len(df_sorted))]
        fig = go.Figure(go.Bar(
            x=df_sorted[model_col],
            y=df_sorted[metric_col],
            marker_color=colors,
            text=[f"{v:.3f}" for v in df_sorted[metric_col]],
            textposition="outside",
        ))
        fig.update_layout(
            title=title,
            xaxis_title="模型",
            yaxis_title=metric_col.upper(),
            height=350,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        return fig

    elif MATPLOTLIB_AVAILABLE:
        _set_chinese_font()
        fig, ax = plt.subplots(figsize=(8, 4))
        colors = ["#2ECC71" if i == 0 else "#1B3A5C"
                  for i in range(len(df_sorted))]
        bars = ax.bar(df_sorted[model_col], df_sorted[metric_col], color=colors)
        ax.set_xlabel("模型")
        ax.set_ylabel(metric_col.upper())
        ax.set_title(title)
        for bar, val in zip(bars, df_sorted[metric_col]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{val:.3f}", ha="center", fontsize=9)
        plt.tight_layout()
        return fig

    return None
