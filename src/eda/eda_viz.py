# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — EDA 可視化圖表生成
Matplotlib + Seaborn，產出 PNG 圖表
"""
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # 非互動後端
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sqlalchemy.engine import Engine

from src.config import OUTPUT_DIR, COLORS
from src.eda.data_quality import check_data_quality
from src.eda.distributions import (
    analyze_hourly_distribution, analyze_weekday_distribution,
    get_7x24_heatmap_data, analyze_peak_hours,
)
from src.eda.district_comparison import (
    analyze_district_comparison, analyze_fee_by_district,
)
from src.utils.logger import log

# 設定中文字體（Windows 用 Microsoft JhengHei）
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
sns.set_style("whitegrid")


def generate_all_eda_charts(engine: Engine, output_dir: Path = None) -> dict:
    """生成所有 EDA 圖表"""
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    log.info("📊 開始生成 EDA 圖表...")

    # 1. 小時分佈
    try:
        path = plot_hourly_distribution(engine, output_dir)
        generated["hourly_distribution"] = str(path)
    except Exception as e:
        log.warning(f"小時分佈圖失敗：{e}")

    # 2. 星期分佈
    try:
        path = plot_weekday_distribution(engine, output_dir)
        generated["weekday_distribution"] = str(path)
    except Exception as e:
        log.warning(f"星期分佈圖失敗：{e}")

    # 3. 7×24 熱力圖
    try:
        path = plot_7x24_heatmap(engine, output_dir)
        generated["heatmap_7x24"] = str(path)
    except Exception as e:
        log.warning(f"7×24 熱力圖失敗：{e}")

    # 4. 18 區對比
    try:
        path = plot_district_comparison(engine, output_dir)
        generated["district_comparison"] = str(path)
    except Exception as e:
        log.warning(f"地區對比圖失敗：{e}")

    # 5. 收費分佈
    try:
        path = plot_fee_distribution(engine, output_dir)
        generated["fee_distribution"] = str(path)
    except Exception as e:
        log.warning(f"收費分佈圖失敗：{e}")

    log.info(f"✅ EDA 圖表生成完成：{len(generated)} 張")
    return generated


def plot_hourly_distribution(engine: Engine, output_dir: Path) -> Path:
    """每小時佔用率分佈折線圖"""
    df = analyze_hourly_distribution(engine)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["hour"], df["avg_occupancy"], color=COLORS["accent"], linewidth=2, marker="o")
    ax.fill_between(df["hour"], df["avg_occupancy"], alpha=0.2, color=COLORS["accent"])
    ax.set_xlabel("小時", fontsize=12)
    ax.set_ylabel("平均佔用率", fontsize=12)
    ax.set_title("全港停車場每小時平均佔用率", fontsize=14, color=COLORS["primary"])
    ax.set_xticks(range(0, 24))
    ax.set_ylim(0, 1)
    ax.axhline(y=0.7, color=COLORS["status_red"], linestyle="--", alpha=0.5, label="繁忙線 70%")
    ax.legend()
    plt.tight_layout()
    path = output_dir / "hourly_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_weekday_distribution(engine: Engine, output_dir: Path) -> Path:
    """星期佔用率長條圖"""
    df = analyze_weekday_distribution(engine)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [COLORS["status_green"] if d in ["週六", "週日"] else COLORS["accent"]
              for d in df["weekday_name"]]
    bars = ax.bar(df["weekday_name"], df["avg_occupancy"], color=colors, alpha=0.8)
    ax.set_xlabel("星期", fontsize=12)
    ax.set_ylabel("平均佔用率", fontsize=12)
    ax.set_title("每星期平均佔用率對比", fontsize=14, color=COLORS["primary"])
    ax.set_ylim(0, 1)
    for bar, val in zip(bars, df["avg_occupancy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.1%}", ha="center", fontsize=10)
    plt.tight_layout()
    path = output_dir / "weekday_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_7x24_heatmap(engine: Engine, output_dir: Path) -> Path:
    """7×24 佔用率熱力圖"""
    pivot = get_7x24_heatmap_data(engine)
    if pivot.empty:
        raise ValueError("無熱力圖數據")

    fig, ax = plt.subplots(figsize=(16, 5))
    sns.heatmap(
        pivot, annot=True, fmt=".0%", cmap="RdYlGn_r",
        vmin=0, vmax=1, ax=ax, cbar_kws={"label": "佔用率"},
        linewidths=0.5,
    )
    ax.set_xlabel("小時", fontsize=12)
    ax.set_ylabel("星期", fontsize=12)
    ax.set_title("7×24 停車場佔用率熱力圖", fontsize=14, color=COLORS["primary"])
    plt.tight_layout()
    path = output_dir / "heatmap_7x24.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_district_comparison(engine: Engine, output_dir: Path) -> Path:
    """18 區佔用率對比長條圖"""
    df = analyze_district_comparison(engine)
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = [COLORS["status_green"] if o < 0.5 else
              COLORS["status_yellow"] if o < 0.7 else COLORS["status_red"]
              for o in df["avg_occupancy"]]
    bars = ax.barh(df["district"], df["avg_occupancy"], color=colors, alpha=0.8)
    ax.set_xlabel("平均佔用率", fontsize=12)
    ax.set_title("18 區停車場平均佔用率排名", fontsize=14, color=COLORS["primary"])
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    for bar, val in zip(bars, df["avg_occupancy"]):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.1%}", va="center", fontsize=9)
    plt.tight_layout()
    path = output_dir / "district_comparison.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def plot_fee_distribution(engine: Engine, output_dir: Path) -> Path:
    """各地區時收費箱型圖"""
    import pandas as pd
    query = "SELECT district, hourly_fee FROM carparks_static WHERE hourly_fee IS NOT NULL"
    df = pd.read_sql(query, engine)

    fig, ax = plt.subplots(figsize=(14, 6))
    districts = sorted(df["district"].unique())
    data = [df[df["district"] == d]["hourly_fee"].values for d in districts]
    bp = ax.boxplot(data, labels=districts, patch_artist=True, vert=True)
    for patch in bp["boxes"]:
        patch.set_facecolor(COLORS["accent"])
        patch.set_alpha(0.6)
    ax.set_xlabel("地區", fontsize=12)
    ax.set_ylabel("時租（HKD）", fontsize=12)
    ax.set_title("18 區停車場時租收費分佈", fontsize=14, color=COLORS["primary"])
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    path = output_dir / "fee_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


if __name__ == "__main__":
    from src.db.connection import get_engine, init_db
    engine = get_engine()
    init_db(engine)
    generate_all_eda_charts(engine)
