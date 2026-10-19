# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 關於
項目介紹 + 痛點 + 數據來源 + 技術棧 + 免責聲明
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.config import COLORS, APP_NAME, APP_VERSION

st.set_page_config(page_title="關於 — 泊得好", page_icon="ℹ️", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>ℹ️ 關於泊得好</h1>", unsafe_allow_html=True)

# ============================================================
# 項目介紹
# ============================================================
st.subheader("🚀 項目介紹")
st.markdown(f"""
**{APP_NAME}** 係一個 Xccelerate Data Science & AI Capstone Project，
目標係解決香港司機「泊車難」嘅問題。

我哋整合香港政府開放數據，運用**時間序列預測**同**機器學習**，
提供全港 18 區、607+ 停車場同 200+ 路邊咪錶嘅：
- 📡 實時空位查詢
- 🔮 未來 30-60 分鐘空位預測
- 💬 自然語言泊車建議（港式中文）
- 🔄 替代停車場推薦
- 💰 收費比較
- 📊 全港空位統計

> 品牌口號：「邊度好泊車？泊得好話你知！」
""")

st.divider()

# ============================================================
# 痛點
# ============================================================
st.subheader("😩 香港泊車痛點")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    ### 🔍 搵位難
    旺角、銅鑼灣、中環呢啲核心商業區，
    周末同放工時間隨時繞幾個圈都搵唔到位，
    浪費時間同油錢。
    """)
with col2:
    st.markdown("""
    ### 💰 收費混亂
    每個停車場收費都唔同，
    時租、日租、夜泊、優惠時段樣樣齊，
    格價要逐個睇，好麻煩。
    """)
with col3:
    st.markdown("""
    ### 🔮 無預測能力
    而家嘅 App 淨係顯示「而家有冇位」，
    唔會話你知「30 分鐘後會唔會滿」，
    去到先發現滿座就白行一趟。
    """)

st.divider()

# ============================================================
# 數據來源
# ============================================================
st.subheader("📊 數據來源")
st.markdown("""
| 數據 | 來源 | 更新頻率 |
|------|------|----------|
| 停車場基本資料 | 香港政府數據一站通 API | 每日 |
| 停車場實時空位 | 香港政府數據一站通 API | 每 5-15 分鐘 |
| 路邊咪錶分佈 | 運輸署 CSV | 每月 |
| 咪錶實時佔用 | 運輸署 API | 每 5 分鐘 |
| 天氣 | 香港天文台開放數據 | 每 10 分鐘 |
""")

st.divider()

# ============================================================
# 技術棧
# ============================================================
st.subheader("🛠️ 技術棧")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    ### 前端
    - Streamlit（多頁面）
    - Folium + OpenStreetMap
    - Plotly / ECharts
    - streamlit-folium

    ### 後端
    - FastAPI（9 端點）
    - Uvicorn
    - Pydantic

    ### 資料庫
    - SQLite（開發）
    - PostgreSQL + TimescaleDB（生產）
    - SQLAlchemy
    """)
with col2:
    st.markdown("""
    ### 機器學習
    - XGBoost（分類）
    - LightGBM（回歸）
    - Prophet（時間序列）
    - 多任務學習（共享底層）
    - Target Encoding

    ### 生成式 AI
    - LangChain 風格 RAG
    - 規則 + 檢索增強
    - 港式繁體中文回應

    ### 部署
    - Streamlit Cloud
    - Docker + Docker Compose
    - GitHub Actions（每小時同步）
    """)

st.divider()

# ============================================================
# 顏色主題
# ============================================================
st.subheader("🎨 品牌設計")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div style='background:{COLORS['primary']};color:white;padding:20px;border-radius:8px;text-align:center;'><b>深藍</b><br>{COLORS['primary']}</div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div style='background:{COLORS['accent']};color:white;padding:20px;border-radius:8px;text-align:center;'><b>青</b><br>{COLORS['accent']}</div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div style='background:{COLORS['status_green']};color:white;padding:20px;border-radius:8px;text-align:center;'><b>綠（充足）</b><br>{COLORS['status_green']}</div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div style='background:{COLORS['status_red']};color:white;padding:20px;border-radius:8px;text-align:center;'><b>紅（滿座）</b><br>{COLORS['status_red']}</div>", unsafe_allow_html=True)

st.divider()

# ============================================================
# 免責聲明
# ============================================================
st.subheader("⚠️ 免責聲明")
st.warning("""
1. **數據來源**：本項目數據來自香港政府數據一站通、運輸署及香港天文台開放數據，僅供學術與教學用途。

2. **預測僅供參考**：空位預測基於歷史數據與機器學習模型，實際情況可能因突發事件（交通事故、大型活動、惡劣天氣）而偏離預測。

3. **收費資訊**：停車場收費可能隨時調整，本項目顯示之收費僅供參考，實際收費以停車場現場公佈為準。標示「估計」的收費為模型推算。

4. **路邊咪錶**：咪錶實時狀態可能有延遲，泊車前請親自確認咪錶狀態與收費。

5. **無商業用途**：本項目為 Xccelerate Capstone 學術項目，不得用於商業營運。

6. **系統可用性**：本項目依賴政府公開 API，不保證 100% 可用；API 中斷時會顯示最近一次快照數據。
""")

st.divider()
st.caption(f"{APP_NAME} v{APP_VERSION} ｜ Xccelerate Data Science & AI Bootcamp Capstone Project")
st.caption("最後更新：2026-10-19")
