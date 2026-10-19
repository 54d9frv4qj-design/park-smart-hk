# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — Folium 地圖可視化
實時地圖、熱力圖、咪錶疊加、Popup 進度條
"""
from typing import List, Dict, Optional
import folium
from folium import plugins
from branca.element import Template, MacroElement

from src.config import COLORS
from src.utils.haversine import status_color, status_label


def create_realtime_map(
    carparks: List[Dict],
    center: tuple = (22.35, 114.13),
    zoom: int = 11,
    show_meters: bool = False,
    meters: List[Dict] = None,
) -> folium.Map:
    """
    建立全港實時停車場地圖
    :param carparks: 停車場列表（含 lat, lng, name, vacancy, total_spaces, status）
    :param center: 地圖中心
    :param zoom: 縮放級別
    :param show_meters: 是否顯示咪錶
    :param meters: 咪錶列表
    """
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    # 停車場 CircleMarker
    for cp in carparks:
        lat, lng = cp.get("lat"), cp.get("lng")
        if not lat or not lng:
            continue

        status = cp.get("status", "unknown")
        color = status_color(status)
        vacancy = cp.get("vacancy", 0)
        total = cp.get("total_spaces", 0)
        occupancy = cp.get("occupancy_rate", 0)

        # Popup HTML（含進度條）
        popup_html = _build_carpark_popup(cp)
        popup = folium.Popup(popup_html, max_width=300)

        # 標記大小按車位數
        radius = max(5, min(15, total / 20)) if total else 8

        folium.CircleMarker(
            location=[lat, lng],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup,
            tooltip=f"{cp.get('name', '')}（{status_label(status)}）",
        ).add_to(m)

    # 咪錶疊加
    if show_meters and meters:
        for mt in meters:
            lat, lng = mt.get("lat"), mt.get("lng")
            if not lat or not lng:
                continue
            status = mt.get("status", "unknown")
            color = status_color(status)
            folium.CircleMarker(
                location=[lat, lng],
                radius=4,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=folium.Popup(_build_meter_popup(mt), max_width=250),
                tooltip=f"咪錶：{mt.get('street_name', '')}",
                icon=folium.DivIcon(html=f'<div style="font-size:12px;">⏱️</div>'),
            ).add_to(m)

    # 圖例
    _add_legend(m)

    return m


def create_heatmap(
    carparks: List[Dict],
    center: tuple = (22.35, 114.13),
    zoom: int = 11,
) -> folium.Map:
    """建立空位熱力圖（佔用率越高越紅）"""
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    heat_data = []
    for cp in carparks:
        lat, lng = cp.get("lat"), cp.get("lng")
        occ = cp.get("occupancy_rate", 0)
        if lat and lng:
            heat_data.append([lat, lng, occ])

    if heat_data:
        plugins.HeatMap(
            heat_data,
            min_opacity=0.3,
            max_zoom=13,
            radius=15,
            blur=10,
            gradient={0.2: "green", 0.5: "yellow", 0.8: "orange", 1.0: "red"},
        ).add_to(m)

    return m


def create_carpark_detail_map(
    carpark: Dict,
    alternatives: List[Dict] = None,
    nearby_meters: List[Dict] = None,
) -> folium.Map:
    """建立單個停車場詳情地圖（含替代停車場與咪錶）"""
    lat, lng = carpark.get("lat"), carpark.get("lng")
    m = folium.Map(location=[lat, lng], zoom_start=15, tiles="OpenStreetMap")

    # 主停車場（大標記）
    folium.Marker(
        location=[lat, lng],
        popup=folium.Popup(_build_carpark_popup(carpark), max_width=300),
        tooltip=carpark.get("name", ""),
        icon=folium.Icon(color="blue", icon="car", prefix="fa"),
    ).add_to(m)

    # 替代停車場
    if alternatives:
        for alt in alternatives:
            folium.CircleMarker(
                location=[alt.get("lat"), alt.get("lng")],
                radius=8,
                color=status_color(alt.get("status", "unknown")),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(_build_carpark_popup(alt), max_width=250),
                tooltip=f"{alt.get('name', '')}（{alt.get('distance_km', '?')}km）",
            ).add_to(m)

    # 附近咪錶
    if nearby_meters:
        for mt in nearby_meters:
            folium.CircleMarker(
                location=[mt.get("lat"), mt.get("lng")],
                radius=5,
                color="purple",
                fill=True,
                fill_color="purple",
                fill_opacity=0.6,
                popup=folium.Popup(_build_meter_popup(mt), max_width=200),
                tooltip=f"咪錶：{mt.get('street_name', '')}",
            ).add_to(m)

    return m


def _build_carpark_popup(cp: Dict) -> str:
    """建立停車場 Popup HTML（含進度條）"""
    vacancy = cp.get("vacancy", 0)
    total = cp.get("total_spaces", 0)
    # 優先用 occupancy_rate，缺省/0 就用 1 - vacancy/total 計算
    occupancy = cp.get("occupancy_rate")
    try:
        occupancy = float(occupancy) if occupancy is not None else None
    except (TypeError, ValueError):
        occupancy = None
    if occupancy is None or occupancy <= 0:
        if total and float(total) > 0 and vacancy is not None:
            occupancy = max(0.0, min(1.0, 1.0 - float(vacancy) / float(total)))
        else:
            occupancy = 0.0
    status = cp.get("status", "unknown")
    color = status_color(status)

    # 30/60 分鐘預測（如有）
    pred_30 = cp.get("prediction_30min", "")
    pred_60 = cp.get("prediction_60min", "")
    pred_html = ""
    if pred_30:
        pred_html += f"<tr><td>30分鐘預測</td><td><b>{pred_30}</b></td></tr>"
    if pred_60:
        pred_html += f"<tr><td>60分鐘預測</td><td><b>{pred_60}</b></td></tr>"

    return f"""
    <div style="font-family: sans-serif; min-width: 220px;">
        <h4 style="color: {COLORS['primary']}; margin: 0 0 8px 0;">{cp.get('name', '')}</h4>
        <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
            <tr><td style="padding: 2px 0;">地區</td><td>{cp.get('district', '')}</td></tr>
            <tr><td style="padding: 2px 0;">空位</td><td><b style="color:{color};">{vacancy} / {total}</b></td></tr>
            <tr><td style="padding: 2px 0;">狀態</td><td><span style="color:{color};font-weight:bold;">{status_label(status)}</span></td></tr>
            <tr><td style="padding: 2px 0;">時租</td><td>HK${cp.get('hourly_fee', 'N/A')}</td></tr>
            {pred_html}
        </table>
        <div style="margin-top: 8px;">
            <div style="background: #e0e0e0; border-radius: 4px; height: 8px;">
                <div style="background: {color}; width: {occupancy*100:.0f}%; height: 8px; border-radius: 4px;"></div>
            </div>
            <small>佔用率 {occupancy*100:.0f}%</small>
        </div>
    </div>
    """


def _build_meter_popup(mt: Dict) -> str:
    """建立咪錶 Popup HTML"""
    return f"""
    <div style="font-family: sans-serif; min-width: 180px;">
        <h4 style="color: #6B5B95; margin: 0 0 6px 0;">⏱️ {mt.get('street_name', '')}</h4>
        <table style="width: 100%; font-size: 12px;">
            <tr><td>地區</td><td>{mt.get('district', '')}</td></tr>
            <tr><td>空位</td><td><b>{mt.get('vacant_spaces', '?')} / {mt.get('total_spaces', '?')}</b></td></tr>
            <tr><td>時租</td><td>HK${mt.get('hourly_fee', 'N/A')}</td></tr>
            <tr><td>最長</td><td>{mt.get('max_duration', 120)}分鐘</td></tr>
        </table>
    </div>
    """


def _add_legend(m: folium.Map) -> None:
    """添加狀態圖例"""
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
         background: white; padding: 10px; border-radius: 8px;
         box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: sans-serif; font-size: 12px;">
        <b style="color: #1B3A5C;">停車場狀態</b><br>
        <span style="display:inline-block;width:12px;height:12px;background:#2ECC71;border-radius:50%;"></span> 充足（>30%）<br>
        <span style="display:inline-block;width:12px;height:12px;background:#F1C40F;border-radius:50%;"></span> 偏緊（10-30%）<br>
        <span style="display:inline-block;width:12px;height:12px;background:#E74C3C;border-radius:50%;"></span> 緊張（<10%）
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
