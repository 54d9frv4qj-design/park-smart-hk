# 🅿️ 泊得好 Park Smart HK
## 香港智能停車：基於時間序列與多源數據的停車場空位預測與推薦系統
### Hong Kong Smart Parking: Time-Series Forecasting and Recommendation System for Parking Vacancy

> **Xccelerate Capstone Project** ｜ 數據科學 × AI 工程 × 全端開發
> 品牌：**泊得好 Park Smart HK** ｜ 口號：「邊度好泊車？泊得好話你知！」

---

## 📋 目錄

- [項目背景與痛點](#-項目背景與痛點)
- [項目目標](#-項目目標)
- [技術架構](#-技術架構)
- [系統架構圖](#-系統架構圖)
- [數據來源](#-數據來源)
- [快速啟動](#-快速啟動)
- [項目目錄結構](#-項目目錄結構)
- [十大交付物總覽](#-十大交付物總覽)
- [公眾網站 8 頁功能](#-公眾網站-8-頁功能)
- [FastAPI 9 端點](#-fastapi-9-端點)
- [機器學習模型](#-機器學習模型)
- [生成式 AI 推薦引擎](#-生成式-ai-推薦引擎)
- [路邊咪錶整合](#-路邊咪錶整合)
- [部署指南](#-部署指南)
- [模擬數據生成器](#-模擬數據生成器)
- [顏色主題與設計規範](#-顏色主題與設計規範)
- [測試與品質保證](#-測試與品質保證)
- [常見問題 FAQ](#-常見問題-faq)
- [免責聲明](#-免責聲明)
- [授權條款](#-授權條款)

---

## 🎯 項目背景與痛點

香港地少人多，**泊車難**係每個車主都遇到嘅問題：

| 痛點 | 場景 |
|------|------|
| **搵位難** | 旺角、銅鑼灣、中環呢啲核心商業區，周末同放工時間隨時繞幾個圈都搵唔到位 |
| **資訊唔透明** | 停車場門口顯示牌經常壞，或者淨係顯示「滿座」，唔知幾時有位 |
| **收費混亂** | 每個停車場收費都唔同，時租、日租、夜泊、優惠時段樣樣齊，格價要逐個睇 |
| **路邊咪錶唔知有冇位** | 見到咪錶就想泊，但行埋先發現全部畀人佔用，白行一趟 |
| **無預測能力** | 而家嘅 App 淨係顯示「而家有冇位」，唔會話你知「30 分鐘後會唔會滿」 |

**泊得好 Park Smart HK** 就係為了解決呢啲問題而生：

> 「邊度好泊車？有冇位？泊車費用幾多？咪錶定停車場抵啲？」
> —— 一個 App，全部答到你。

---

## 🚀 項目目標

建立一個涵蓋**數據工程、機器學習、可視化、生成式 AI 與公眾網站**嘅完整系統：

1. **實時查詢**：全港 18 區、607+ 停車場及 200+ 路邊咪錶組嘅即時空位
2. **未來預測**：基於時間序列模型，預測未來 30–60 分鐘空位情況
3. **自然語言建議**：用港式繁體中文同你傾，「而家去邊度泊最抵？」
4. **替代推薦**：目標停車場滿座時，自動推薦附近 5 個替代選擇
5. **收費比較**：並列顯示時租、日租、夜泊收費，幫你慳錢
6. **全港統計**：邊區最易泊、邊區最緊張、7×24 時段熱力圖

---

## 🛠️ 技術架構

| 層級 | 技術 | 說明 |
|------|------|------|
| **前端** | Streamlit（多頁面） | 8 頁公眾網站，Folium 地圖，ECharts 圖表 |
| **後端** | FastAPI | RESTful API，9 個端點，自動生成 OpenAPI 文檔 |
| **資料庫** | SQLite（開發）/ PostgreSQL + TimescaleDB（生產） | 時間序列優化，高效儲存 190 萬+ 歷史記錄 |
| **機器學習** | XGBoost / LightGBM / Prophet / 多任務學習 | 分類 + 回歸 + 時間序列，跨場 Target Encoding |
| **生成式 AI** | LangChain 風格 RAG（規則 + 檢索增強） | 自然語言查詢解析、推薦排序、港式繁中回應 |
| **地圖** | Folium + OpenStreetMap | 無需 API Key，CircleMarker 狀態色編碼 |
| **部署** | Streamlit Cloud / Render / AWS EC2 | 三方案，含成本估算 |
| **定時同步** | GitHub Actions（每小時）+ App 內每 10 分鐘 | 自動抓取政府 API，保持數據新鮮 |
| **版本控制** | Git + GitHub | CI/CD 自動測試 |

### 技術棧總覽

```
前端：Streamlit · Folium · streamlit-echarts · streamlit-folium
後端：FastAPI · Uvicorn · Pydantic
數據：Pandas · NumPy · SQLAlchemy · APScheduler
ML：scikit-learn · XGBoost · LightGBM · Prophet · statsmodels
GenAI：OpenAI · LangChain · ChromaDB · tiktoken
可視化：Matplotlib · Seaborn · Plotly · Folium
地理：geopy · Haversine
DB：SQLite · psycopg2 · asyncpg
測試：pytest · httpx · Streamlit AppTest
```

---

## 🏗️ 系統架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        香港政府開放數據（Data.Gov.HK）                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ 停車場基本資料 │  │ 停車場實時空位 │  │ 咪錶分佈 CSV  │  │ 咪錶實時狀態│  │
│  │  basic_info  │  │  vacancy     │  │ parkingspaces│  │ occupancy  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                 │                │         │
│         └─────────────────┴────────┬────────┴────────────────┘         │
│                                    │                                    │
│  ┌─────────────────────────────────┴─────────────────────────────────┐ │
│  │              香港天文台開放數據（HKO Open Data）                    │ │
│  │         實時天氣 · 雨量 · 溫度 · 濕度 · 警告訊息                    │ │
│  └─────────────────────────────────┬─────────────────────────────────┘ │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │         ETL 管線                 │
                    │  抓取 → 清洗 → 正則化 → 空間匹配  │
                    │  · 統一時間格式（HKT, UTC+8）     │
                    │  · 提取經緯度（WGS84）            │
                    │  · 咪錶同街道空間插值              │
                    │  · 停車場×咪錶 Haversine 匹配     │
                    │  · 錯誤處理 + 降級模擬數據         │
                    └────────────────┬────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
┌─────────▼─────────┐    ┌──────────▼──────────┐    ┌──────────▼──────────┐
│  SQLite（開發）    │    │ PostgreSQL +         │    │  模擬數據生成器       │
│  smart_parking.db │    │ TimescaleDB（生產）   │    │  Mock Data Generator │
│  4 核心表 + 索引   │    │  時間序列分區         │    │  607 停車場           │
│                   │    │  190 萬+ 記錄         │    │  200 咪錶組           │
└─────────┬─────────┘    └──────────┬──────────┘    │  30 天歷史            │
          │                         │               └──────────┬──────────┘
          └────────────┬────────────┘                          │
                       │                                       │
        ┌──────────────▼──────────────┐                        │
        │     特徵工程 + 模型訓練       │                        │
        │  · 時間特徵（時/日/週末/尖峰）│                        │
        │  · 滯後特徵（15/30/60min）   │                        │
        │  · 滑動窗口（均值/標準差）    │                        │
        │  · 天氣特徵                  │                        │
        │  · car_park_id Target Enc.  │◄───────────────────────┘
        │  · 多任務學習（共享底層）     │
        └──────────────┬──────────────┘
                       │ .pkl
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼────┐  ┌─────────▼──────┐  ┌────────▼────────┐
│ Prophet │  │  XGBoost       │  │  LightGBM       │
│ 時間序列│  │  分類（有冇位） │  │  回歸（空位數）  │
└───┬────┘  └─────────┬──────┘  └────────┬────────┘
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │     生成式 AI 推薦引擎        │
        │  · query_parser（意圖解析）   │
        │  · recommender（排序推薦）    │
        │  · RAG（檢索增強）            │
        │  · 港式繁體中文回應           │
        └──────────────┬──────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼──────────┐  ┌───▼──────────┐  ┌───▼───────────┐
│  FastAPI     │  │  Streamlit   │  │  定時同步      │
│  後端 API    │  │  前端網站     │  │  Worker       │
│  9 端點      │  │  8 頁面       │  │  GitHub Actions│
│  /docs 文檔  │  │  Folium 地圖  │  │  每小時        │
└──────────────┘  └──────────────┘  └───────────────┘
```

---

## 📊 數據來源

### 主要數據源（香港政府數據一站通）

| 數據 | API 端點 | 說明 | 更新頻率 |
|------|----------|------|----------|
| 停車場基本資料 | `https://api.data.gov.hk/v1/carpark-info-vacancy?data=basic` | 名稱、地址、經緯度、車位總數、收費 | 每日 |
| 停車場實時空位 | `https://api.data.gov.hk/v1/carpark-info-vacancy?data=vacancy&vehicleTypes=privateCar&lang=zh_TW` | 私家車/電動車/貨車即時空位 | 每 5–15 分鐘 |
| 咪錶泊車位分佈 | 運輸署 CSV | 咪錶位置、車位數、收費 | 每月 |
| 新咪錶使用情況 | 運輸署 API | 實時佔用狀態（V=空置/O=佔用） | 每 5 分鐘 |

### 輔助數據源

| 數據 | 來源 | 說明 |
|------|------|------|
| 天氣 | 香港天文台開放數據 | 實時氣溫、濕度、雨量、天氣警告 |
| 歷史數據 | 自行收集 | 2026-09-15 至 2026-10-15，每 15 分鐘快照，約 190 萬條記錄 |

### API JSON 結構關鍵欄位

```json
// 停車場實時空位（privateCar）
{
  "park_Id": "1001",
  "name": "中環天星碼頭停車場",
  "district": "中西區",
  "address": "中環民光街",
  "lat": 22.2855,
  "lng": 114.1610,
  "vehicleTypes": {
    "privateCar": {
      "space": 120,        // 總車位
      "spaceEV": 10,       // 電動車位
      "vacancy": 35        // 即時空位
    }
  },
  "parkingCharges": {
    "hourly": 30,
    "daily": 300,
    "monthly": 4500
  },
  "updateTime": "2026-10-19T14:30:00+08:00"
}
```

### CSDI API 403 處理

> ⚠️ **已知問題**：CSDI（`portal.csdi.gov.hk`）部分 FeatureServer 會回傳 `403 Forbidden` 或 `499 Token Required`。
>
> **解決方案**：
> 1. 加上瀏覽器式 `User-Agent` Header + 正確 ArcGIS 查詢參數
> 2. 如仍需 Token，到 CSDI 門戶註冊免費帳號取得
> 3. **本項目已內建模擬數據生成器**，API 失敗時自動降級，確保離線可運行

---

## ⚡ 快速啟動

### 環境要求

- Python **3.11 – 3.12**（建議 3.11，Streamlit Cloud 支援）
- Git
- （可選）Docker & Docker Compose

### 步驟一：複製倉庫

```bash
git clone https://github.com/your-username/hongkong-smart-parking.git
cd hongkong-smart-parking
```

### 步驟二：建立虛擬環境並安裝依賴

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements-dev.txt
```

### 步驟三：設定環境變數

```bash
# 複製範本
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# 編輯 .env，填入（可選）OPENAI_API_KEY
```

### 步驟四：初始化資料庫（含模擬數據）

```bash
# 建立 Schema + 填入 607 停車場 + 200 咪錶 + 30 天歷史模擬數據
python scripts/init_db.py --mock
```

### 步驟五：啟動服務

```bash
# 選項 A：一鍵啟動 FastAPI 後端
make api
# → http://localhost:8000  （API 文檔：/docs）

# 選項 B：啟動 Streamlit 前端
make streamlit
# → http://localhost:8501

# 選項 C：Docker 完整啟動（API + Worker + PostgreSQL）
make docker-up
```

### 步驟六：執行測試

```bash
# 全部測試（含冒煙測試）
make test

# 僅冒煙測試
pytest tests/ -m smoke -v
```

---

## 📁 項目目錄結構

```
hongkong-smart-parking/
├── README.md                          # 📖 本文件（項目說明）
├── requirements.txt                   # Python 生產依賴
├── requirements-dev.txt               # 開發+測試依賴
├── .gitignore                         # Git 忽略規則
├── .env.example                       # 環境變數範本
├── Makefile                           # 快捷指令（make help）
├── pytest.ini                         # pytest 配置
├── Dockerfile                         # Docker 映像建置
├── docker-compose.yml                 # API + Worker + PostgreSQL
│
├── .streamlit/
│   └── config.toml                    # Streamlit 主題（深藍+青）
│
├── .github/
│   └── workflows/
│       ├── ci.yml                     # CI：語法檢查 + 冒煙測試
│       └── sync_data.yml              # 每小時政府 API 同步
│
├── docs/                              # 📚 項目文檔
│   ├── architecture.md                # 系統架構詳解
│   ├── api_design.md                  # FastAPI 設計文檔
│   ├── deployment.md                  # 部署指南（三方案）
│   ├── data_dictionary.md             # 數據字典
│   ├── model_report.md                # 模型評估報告
│   └── website/                       # 公眾網站文檔
│       ├── site_architecture.md       # 網站架構圖（頁面流程/系統/數據流/組件）
│       ├── user_guide.md              # 7 頁使用說明 + 搜尋技巧 + FAQ
│       ├── wireframes.md              # 7 頁 ASCII 線框圖 + 響應式描述
│       └── integration.md             # 網站與現有項目整合方式
│
├── data/                              # 💾 數據目錄（gitignore）
│   ├── raw/                           # 原始 API 響應
│   ├── processed/                     # 清洗後數據
│   └── smart_parking.db               # SQLite 資料庫
│
├── models/                            # 🤖 訓練好的模型（gitignore）
│   ├── prophet_*.pkl                  # Prophet 時間序列模型
│   ├── xgboost_*.pkl                  # XGBoost 分類模型
│   ├── lightgbm_*.pkl                 # LightGBM 回歸模型
│   ├── multitask_*.pkl                # 多任務學習模型
│   └── target_encoder.pkl             # 跨場 Target Encoder
│
├── output/                            # 📊 EDA 輸出（gitignore）
│   ├── geo_heatmap.html               # 全港地理熱力圖
│   ├── district_comparison.png        # 地區對比
│   ├── timeseries_7x24_heatmap.png    # 7×24 時段熱力圖
│   ├── model_performance.png          # 模型表現
│   └── ...
│
├── notebooks/                         # 📓 Jupyter 探索筆記
│   ├── 01_eda.ipynb                   # 探索性數據分析
│   └── 02_modeling.ipynb              # 建模實驗
│
├── src/                               # 🔧 核心源碼
│   ├── __init__.py
│   ├── config.py                      # 全局配置（URL/路徑/常數/顏色）
│   │
│   ├── mock_data/                     # 🎲 模擬數據生成器
│   │   ├── __init__.py
│   │   ├── carpark_generator.py       # 停車場模擬（607 個，18 區）
│   │   ├── meter_generator.py         # 咪錶模擬（200 組，空間插值）
│   │   └── weather_generator.py       # 天氣模擬（HKO 格式）
│   │
│   ├── data_fetch/                    # 📡 數據抓取
│   │   ├── __init__.py
│   │   ├── carpark_api.py             # 停車場基本+實時 API
│   │   ├── meter_api.py               # 咪錶分佈+實時 API
│   │   └── weather_api.py             # 香港天文台 API
│   │
│   ├── etl/                           # 🔄 ETL 管線
│   │   ├── __init__.py
│   │   ├── etl_pipeline.py            # 主 ETL 流程
│   │   ├── cleaners.py                # 數據清洗（缺失值/異常值）
│   │   └── spatial_join.py            # Haversine 空間匹配
│   │
│   ├── db/                            # 🗄️ 資料庫
│   │   ├── __init__.py
│   │   ├── schema.sql                 # SQL Schema（4 核心表+索引）
│   │   ├── connection.py              # 連接管理（SQLite/PostgreSQL）
│   │   └── queries.py                 # 常用查詢函數
│   │
│   ├── eda/                           # 📈 探索性數據分析
│   │   ├── __init__.py
│   │   ├── data_quality.py            # 數據質量檢查
│   │   ├── distributions.py           # 時段分佈分析
│   │   ├── district_comparison.py     # 18 區對比
│   │   └── eda_viz.py                 # 可視化圖表生成
│   │
│   ├── models/                        # 🧠 機器學習
│   │   ├── __init__.py
│   │   ├── feature_engineering.py     # 特徵工程（時間/滯後/窗口/天氣）
│   │   ├── target_encoding.py         # car_park_id Target Encoding
│   │   ├── prophet_model.py           # Prophet 時間序列
│   │   ├── xgboost_model.py           # XGBoost 分類
│   │   ├── lightgbm_model.py          # LightGBM 回歸
│   │   ├── multitask_model.py         # 多任務學習（共享底層+每場輸出頭）
│   │   ├── evaluate.py                # 模型評估（MAE/RMSE/F1）
│   │   └── train_all.py               # 一鍵訓練所有模型
│   │
│   ├── genai/                         # 🤖 生成式 AI
│   │   ├── __init__.py
│   │   ├── query_parser.py            # 自然語言意圖解析
│   │   ├── recommender.py             # 推薦排序算法
│   │   ├── response_generator.py      # 港式繁體中文回應生成
│   │   └── rag_engine.py              # 檢索增強對話引擎
│   │
│   ├── api/                           # 🌐 FastAPI 後端
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 應用入口
│   │   ├── schemas.py                 # Pydantic 請求/響應模型
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── overview.py            # GET /api/overview
│   │       ├── map.py                 # GET /api/map
│   │       ├── detail.py              # GET /api/detail/{park_id}
│   │       ├── alternatives.py        # GET /api/alternatives/{park_id}
│   │       ├── meters.py              # GET /api/meters
│   │       ├── dashboard.py           # GET /api/dashboard
│   │       ├── search.py              # GET /api/search
│   │       ├── chat.py                # POST /api/chat
│   │       └── fees.py                # GET /api/fees
│   │
│   ├── visualization/                 # 🎨 可視化組件
│   │   ├── __init__.py
│   │   ├── maps.py                    # Folium 地圖（實時/熱力/咪錶疊加）
│   │   ├── heatmaps.py                # 7×24 熱力圖
│   │   └── charts.py                  # ECharts/Matplotlib 圖表
│   │
│   └── utils/                         # 🧰 工具函數
│       ├── __init__.py
│       ├── logger.py                  # Loguru 日誌配置
│       ├── haversine.py               # 球面距離計算
│       └── time_utils.py              # 時間處理（HKT/時段判斷）
│
├── streamlit_app/                     # 🖥️ Streamlit 公眾網站（8 頁）
│   ├── Home.py                        # 🏠 首頁（搜尋+統計+地圖+Top5）
│   └── pages/
│       ├── 1_實時地圖.py               # 🗺️ 全港實時地圖（607 CircleMarker）
│       ├── 2_停車場詳情.py             # 📋 停車場詳情（預測+歷史+替代+AI建議）
│       ├── 3_AI對話.py                 # 💬 AI 對話（港式用語+5 快捷問題）
│       ├── 4_路邊咪錶.py               # ⏱️ 路邊咪錶（地圖+列表+收費+對比）
│       ├── 5_儀表板.py                 # 📊 儀表板（統計+排名+熱力圖+趨勢）
│       ├── 6_收費比較.py               # 💰 收費比較（26 真實+581 估計）
│       └── 7_關於.py                   # ℹ️ 關於（項目+痛點+數據+免責）
│
├── tests/                             # ✅ 測試
│   ├── __init__.py
│   ├── conftest.py                    # pytest fixture（模擬 DB）
│   ├── test_api_smoke.py              # FastAPI 6+ 端點冒煙測試
│   ├── test_streamlit_smoke.py        # Streamlit 8 頁 AppTest 冒煙測試
│   ├── test_etl.py                    # ETL 管線測試
│   └── test_models.py                 # 模型訓練與預測測試
│
├── scripts/                           # 📜 獨立腳本
│   ├── init_db.py                     # 初始化資料庫（--mock 填入模擬數據）
│   ├── sync_realtime.py               # 實時同步（GitHub Actions 每小時）
│   └── train_models.py                # 一鍵訓練所有模型
│
├── run_pipeline.py                    # 🚀 一鍵管線（ETL → 訓練 → EDA）
└── app.py                             # （舊版單頁入口，保留相容）
```

---

## 📦 十大交付物總覽

### 第一階段：基礎項目（8 項）

| # | 交付物 | 核心內容 | 狀態 |
|---|--------|----------|------|
| 1 | **GitHub 倉庫結構 + README.md** | 完整目錄樹、技術棧、快速啟動、數據來源、免責聲明 | ✅ 本文件 |
| 2 | **SQL 資料庫 Schema** | 4 核心表（停車場靜態/實時、咪錶、天氣）+ 索引 + TimescaleDB 分區 | ⏳ 待產出 |
| 3 | **API 抓取與 ETL 代碼** | 政府 API 客戶端、清洗、正則化、空間匹配、錯誤處理、模擬降級 | ⏳ 待產出 |
| 4 | **EDA 代碼與報告** | 數據質量、缺失值、時段分佈、18 區對比、相關性分析、可視化 | ⏳ 待產出 |
| 5 | **時間序列與 ML 建模** | 特徵工程、Prophet、XGBoost、LightGBM、Target Encoding、多任務學習、評估報告 | ⏳ 待產出 |
| 6 | **可視化儀表板** | Streamlit 全港統計、地區排名、7×24 熱力圖、14 天趨勢、模型表現 | ⏳ 待產出 |
| 7 | **生成式 AI 推薦系統** | query_parser、recommender、原因解釋、替代選擇、港式繁中回應 | ⏳ 待產出 |
| 8 | **路邊咪錶整合** | 200 咪錶組 ETL、同街道空間插值、停車場×咪錶 Haversine 融合 | ⏳ 待產出 |

### 第二階段：實時部署（1 項）

| # | 交付物 | 核心內容 | 狀態 |
|---|--------|----------|------|
| 9 | **實時部署** | Docker（API+Worker+PostgreSQL）、Cloud Run Job（每 10 分鐘）、FastAPI 6 端點冒煙測試 | ⏳ 待產出 |

### 第三階段：公眾網站（1 項，含 10 子項）

| # | 交付物 | 核心內容 | 狀態 |
|---|--------|----------|------|
| 10 | **「泊得好」公眾網站** | a.架構圖 b.8頁Streamlit c.9端點API d.DB查詢 e.地圖可視化 f.GenAI對話 g.部署 h.使用說明 i.線框圖 j.整合文檔 | ⏳ 待產出 |

### 第四階段：數據與部署優化（4 項）

| # | 交付物 | 核心內容 | 狀態 |
|---|--------|----------|------|
| 11 | **政府 API 實時同步** | 每小時自動呼叫、清洗寫入 DB、錯誤處理與日誌 | ⏳ 待產出 |

---

## 🖥️ 公眾網站 8 頁功能

### 🏠 首頁（Home）
- **搜尋欄**：支援地點 / 名稱 / 地區 / 車型 / 時段
- **統計卡**：全港停車場總數、總空位、平均佔用率、最易泊時段
- **Folium 地圖**：全港停車場分佈預覽
- **Top 5 排名**：最易泊停車場 + 最緊張停車場

### 🗺️ 實時地圖（Real-time Map）
- 全港 **607+ 停車場** CircleMarker
- **顏色編碼**：🟢 綠（空位 >30%）／🟡 黃（10–30%）／🔴 紅（<10% 或滿座）
- Popup 含：即時空位、**30/60 分鐘預測**、收費、地址
- 側邊欄篩選：地區、車型、收費範圍、狀態

### 📋 停車場詳情（Parking Detail）
- 即時狀態大卡片（空位數 / 總數 / 佔用率進度條）
- **未來預測圖**：30–60 分鐘空位走勢
- **24 小時歷史圖**：今日空位變化
- **7×24 繁忙熱力圖**：星期×小時佔用率
- **附近替代停車場**：5 個最近選擇（含距離、空位、收費）
- **GenAI 自然語言建議**：「而家去呢度泊，建議你...」
- **Google Maps / Waze 導航**按鈕

### 💬 AI 對話（AI Chat）
- Streamlit chat 界面，對話歷史保存
- **query_parser** 解析意圖（搵位/格價/預測/咪錶）
- **recommender** 排序推薦
- **5 個快捷問題**：
  1. 「而家旺角邊度有位泊？」
  2. 「中環邊個停車場最平？」
  3. 「30 分鐘後銅鑼灣會唔會滿？」
  4. 「附近有冇路邊咪錶？」
  5. 「今晚夜泊邊度抵？」
- 全程**港式繁體中文**，用語自然貼地

### ⏱️ 路邊咪錶（Meter Parking）
- 咪錶地圖（200+ 組）+ 列表切換
- 實時佔用狀態（V=空置 / O=佔用）
- **未來預測**：咪錶組空位預測
- 收費資訊：時租、最長泊車時間、支付方式
- **咪錶 vs 停車場對比圖**：價格、便利性、空位率

### 📊 儀表板（Dashboard）
- 全港統計：總停車場、總車位、平均佔用率、趨勢
- **18 區排名**：由易泊到緊張
- **星期×小時熱力圖**：一週繁忙模式
- **14 天趨勢**：全港空位走勢
- **模型表現**：MAE / RMSE / F1-Score 對比

### 💰 收費比較（Fee Comparison）
- **26 個政府場真實收費** + **581 個估計收費**
- 並列顯示：時租 / 日租 / 夜泊 / 月票
- 篩選：地區、車型、收費類型
- 排序：由平到貴 / 由貴到平
- 標記「最抵泊」推薦

### ℹ️ 關於（About）
- 項目介紹與品牌故事
- 香港泊車痛點分析
- 數據來源與更新頻率
- 技術棧詳解
- 團隊成員（如適用）
- **免責聲明**

---

## 🌐 FastAPI 9 端點

| 方法 | 端點 | 說明 | 關鍵參數 |
|------|------|------|----------|
| GET | `/api/overview` | 全港統計總覽 | — |
| GET | `/api/map` | 地圖數據（所有停車場位置+狀態） | `district`, `vehicle_type` |
| GET | `/api/detail/{park_id}` | 單個停車場詳情 | `park_id` |
| GET | `/api/alternatives/{park_id}` | 替代停車場推薦 | `park_id`, `limit=5`, `radius_km=1` |
| GET | `/api/meters` | 路邊咪錶列表/地圖數據 | `district`, `status` |
| GET | `/api/dashboard` | 儀表板數據 | `days=14` |
| GET | `/api/search` | 搜尋停車場/咪錶 | `q`, `district`, `vehicle_type` |
| POST | `/api/chat` | AI 對話 | `message`, `history` |
| GET | `/api/fees` | 收費比較數據 | `district`, `sort_by` |

> API 文檔自動生成：啟動後訪問 `http://localhost:8000/docs`（Swagger UI）

---

## 🧠 機器學習模型

### 特徵工程（`feature_engineering.py`）

| 特徵類別 | 具體特徵 |
|----------|----------|
| **時間特徵** | 小時、星期幾、是否週末、是否公眾假期、是否尖峰時段（早 7–9 / 晚 5–7） |
| **滯後特徵** | 15 分鐘前、30 分鐘前、60 分鐘前空位數 |
| **滑動窗口** | 過去 30/60/120 分鐘均值、標準差、趨勢斜率 |
| **天氣特徵** | 氣溫、濕度、雨量、是否有天氣警告 |
| **場地特徵** | 總車位數、地區、是否政府場、是否有 EV 充電 |
| **Target Encoding** | `car_park_id` 跨場 Target Encoding（平滑處理，避免過擬合） |

### 模型一覽

| 模型 | 任務 | 輸出 | 評估指標 |
|------|------|------|----------|
| **Prophet** | 時間序列預測 | 未來 30/60 分鐘空位 + 置信區間 | MAE, RMSE, MAPE |
| **XGBoost** | 分類 | 未來 30 分鐘「是否有空位」機率 | F1-Score, AUC-ROC |
| **LightGBM** | 回歸 | 未來 30/60 分鐘具體空位數 | MAE, RMSE, R² |
| **多任務學習** | 共享底層 + 每場輸出頭 | 多停車場聯合預測 | 平均 MAE / RMSE |

### 跨場 Target Encoding

- 對 `car_park_id` 進行 Target Encoding，編碼目標為歷史平均佔用率
- 使用**平滑參數**避免小樣本停車場過擬合
- Encoder 隨模型一起保存，預測時一致使用

### 多任務學習架構

```
輸入特徵（共享）
    │
    ▼
┌─────────────┐
│  共享底層     │  （學習全港通用模式：時間/天氣/地區影響）
│  Dense × 3   │
└──────┬──────┘
       │
   ┌───┴───┬───────┐
   ▼       ▼       ▼
┌─────┐ ┌─────┐ ┌─────┐
│場1頭│ │場2頭│ │場N頭│  （每個停車場獨立輸出頭）
│Dense│ │Dense│ │Dense│
└──┬──┘ └──┬──┘ └──┬──┘
   ▼       ▼       ▼
 空位預測  空位預測  空位預測
```

---

## 🤖 生成式 AI 推薦引擎

### 架構（LangChain 風格：規則 + 檢索增強）

```
用戶輸入（港式中文）
    │
    ▼
┌──────────────────┐
│  query_parser     │  意圖分類：搵位 / 格價 / 預測 / 咪錶 / 夜泊
│  （規則+關鍵詞）   │  實體提取：地區 / 停車場名 / 時間 / 車型
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│檢索 DB  │ │檢索 RAG│  從向量庫檢索相關收費規則、
│實時數據 │ │知識庫  │  泊車貼士、地區經驗
└───┬────┘ └───┬────┘
    └────┬─────┘
         ▼
┌──────────────────┐
│  recommender      │  加權排序：距離(30%) + 空位率(30%)
│  （加權排序）      │  + 收費(20%) + 預測趨勢(20%)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ response_generator│  港式繁體中文回應
│  （模板+LLM）     │  含原因解釋 + 替代選擇 + 行動建議
└──────────────────┘
```

### 港式用語示例

| 場景 | 回應示例 |
|------|----------|
| 搵位 | 「而家旺角區最易泊係**新世紀廣場**，仲有 45 個位，30 分鐘後預測仲有 38 個，建議你而家去！」 |
| 滿座替代 | 「**又一城**而家滿座喇，附近 500 米有**又一城商場停車場**（28 位）同**九龍塘站**（15 位），後者平 5 蚊個鐘。」 |
| 格價 | 「中環時租最平係**天星碼頭**（$25/hr），最貴係**國際金融中心**（$50/hr），夜晚 8 點後全部半價。」 |
| 預測 | 「銅鑼灣而家空位率 15%（偏緊），60 分鐘後預測升到 25%，建議你遲少少去或者揀**時代廣場**。」 |

> 無 OpenAI API Key 時自動降級為**規則式回應**，確保功能可用。

---

## ⏱️ 路邊咪錶整合

### 數據管線

1. **抓取**：運輸署咪錶分佈 CSV + 新咪錶實時佔用 API
2. **清洗**：統一咪錶編號、提取經緯度、正則化收費（時租/最長時間）
3. **空間插值**：同一街道咪錶組內，若個別咪錶數據缺失，用相鄰咪錶狀態插值
4. **停車場×咪錶融合**：Haversine 公式計算每個停車場方圓 500 米內嘅咪錶組，建立空間關聯

### Haversine 空間匹配

```python
# 球面距離公式（公里）
def haversine(lat1, lng1, lat2, lng2):
    R = 6371  # 地球半徑（km）
    ...
    return distance

# 為每個停車場匹配方圓 500m 內嘅咪錶組
for carpark in carparks:
    nearby_meters = [
        m for m in meters
        if haversine(carpark.lat, carpark.lng, m.lat, m.lng) <= 0.5
    ]
```

### 咪錶 vs 停車場對比

| 維度 | 路邊咪錶 | 停車場 |
|------|----------|--------|
| 收費 | 通常較平（$4–$16/hr） | 較貴（$20–$50/hr） |
| 最長時間 | 通常 2 小時 | 無限制 |
| 便利性 | 路邊即泊即走 | 要行入去 |
| 空位率 | 變化大，熱門區長期滿 | 相對穩定 |
| 惡天氣 | 暴露在街上 | 室內/有蓋 |

---

## 🚀 部署指南

### 方案一：Streamlit Cloud（推薦，免費）

**優點**：免費、自動 HTTPS、GitHub 一鍵部署
**限制**：`/mount/src/` 唯讀，DB 同模型必須放 `/tmp/`

```toml
# .streamlit/secrets.toml（喺 Streamlit Cloud Secrets 設定）
DATABASE_URL = "sqlite:////tmp/smart_parking.db"
OPENAI_API_KEY = "sk-..."
```

**步驟**：
1. Push 到 GitHub
2. 到 <https://share.streamlit.io> → New app
3. Repository：你的倉庫 ｜ Branch：`main` ｜ Main file：`streamlit_app/Home.py`
4. Secrets 填入 `DATABASE_URL`（用 `/tmp/` 路徑）同 `OPENAI_API_KEY`
5. Deploy！

**成本**：免費（開源專案）

### 方案二：Render（後端+前端分離）

**優點**：支援 FastAPI + PostgreSQL、自動 HTTPS、免費層可用
**步驟**：
1. Web Service：Dockerfile 部署 FastAPI（$0–$7/月）
2. PostgreSQL：Render Managed DB（$0–$7/月）
3. Streamlit：獨立 Web Service 或用 Streamlit Cloud
4. 設定環境變數 `DATABASE_URL`

**成本估算**：約 **$7–$15/月**（生產級）

### 方案三：AWS EC2（完全控制）

**優點**：完全控制、可跑 PostgreSQL + TimescaleDB + Worker
**步驟**：
1. 啟動 EC2（t3.micro 免費層 / t3.small $15/月）
2. 安裝 Docker + Docker Compose
3. `docker-compose up -d`（API + Worker + PostgreSQL）
4. 設定 Nginx 反向代理 + Let's Encrypt SSL
5. 設定 CloudWatch 監控

**成本估算**：
| 資源 | 規格 | 月費 |
|------|------|------|
| EC2 | t3.small | ~$15 |
| EBS | 30 GB gp3 | ~$3 |
| 數據傳輸 | 100 GB | ~$9 |
| **合計** | | **~$27/月** |

### 定時同步配置

- **GitHub Actions**：每小時自動呼叫 `scripts/sync_realtime.py`（`.github/workflows/sync_data.yml`）
- **App 內刷新**：Streamlit 每 10 分鐘自動檢查新數據（`@st.cache_data(ttl=600)`）
- **Docker Worker**：生產環境用 APScheduler 每 10 分鐘同步

---

## 🎲 模擬數據生成器

> 因政府 API 可能因 403 / 限流 / 網絡問題無法訪問，本項目內建**完整模擬數據生成器**，確保離線可運行。

### 生成內容

| 數據 | 數量 | 模擬邏輯 |
|------|------|----------|
| 停車場 | 607 個 | 按 18 區人口密度分配，中區/灣仔/油尖旺最密集 |
| 咪錶組 | 200 組 | 按街道分佈，每組 2–8 個咪錶 |
| 歷史記錄 | ~190 萬條 | 每 15 分鐘快照，30 天，含工作日/週末/雨天模式 |
| 天氣 | 30 天 | 模擬 HKO 格式，含晴/雲/雨/颱風 |

### 模擬規則

- **早晚尖峰**：週一至五 7–9AM、5–7PM 佔用率最高（85–95%）
- **午飯時段**：12–2PM 商業區偏高（70–85%）
- **週末模式**：購物區（銅鑼灣/尖沙咀）下午最高，住宅區相反
- **雨天效應**：下雨時自駕增加，佔用率 +10–15%
- **隨機波動**：加入正態分佈噪聲，模擬真實變化

### 使用方式

```bash
# 初始化時自動填入
python scripts/init_db.py --mock

# ETL 管線中 API 失敗時自動降級
python run_pipeline.py --etl   # API 失敗 → 自動用模擬數據
```

---

## 🎨 顏色主題與設計規範

### 品牌色板

| 用途 | 顏色 | HEX |
|------|------|-----|
| 主色（深藍） | 深藍 | `#1B3A5C` |
| 強調色（青） | 青藍 | `#00A8B5` |
| 背景 | 白色 | `#FFFFFF` |
| 次要背景 | 淺灰藍 | `#F0F4F8` |
| 文字 | 深藍 | `#1B3A5C` |

### 狀態色（停車場空位）

| 狀態 | 顏色 | HEX | 條件 |
|------|------|-----|------|
| 🟢 充足 | 綠色 | `#2ECC71` | 空位率 > 30% |
| 🟡 偏緊 | 黃色 | `#F1C40F` | 空位率 10–30% |
| 🔴 滿座 | 紅色 | `#E74C3C` | 空位率 < 10% |

### Streamlit 主題配置（`.streamlit/config.toml`）

```toml
[theme]
base = "light"
primaryColor = "#00A8B5"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F4F8"
textColor = "#1B3A5C"
font = "sans serif"
```

---

## ✅ 測試與品質保證

### 測試覆蓋

| 測試類型 | 工具 | 覆蓋範圍 |
|----------|------|----------|
| **FastAPI 冒煙測試** | pytest + httpx | 9 端點全部可訪問、返回 200、JSON 格式正確 |
| **Streamlit AppTest** | Streamlit AppTest | 8 頁面全部可渲染、無異常、關鍵元件存在 |
| **ETL 管線測試** | pytest | 模擬數據輸入 → 清洗 → 寫入 DB → 驗證 |
| **模型測試** | pytest | 特徵工程 → 訓練（小數據）→ 預測 → 評估 |
| **語法檢查** | compileall | 所有 .py 可編譯 |
| **程式碼品質** | black + flake8 + isort | 格式化、Lint、Import 排序 |

### 執行測試

```bash
# 全部測試
make test

# 僅冒煙測試（快速）
pytest tests/ -m smoke -v

# 程式碼品質檢查
make lint
```

### CI/CD

- **Push / PR**：自動執行語法檢查 + 冒煙測試（`.github/workflows/ci.yml`）
- **每小時**：自動同步政府 API 數據（`.github/workflows/sync_data.yml`）

---

## ❓ 常見問題 FAQ

**Q1：政府 API 返 403 點算？**
A：本項目已內建模擬數據生成器，API 失敗時自動降級。如需真實數據，可檢查網絡、加上 User-Agent Header，或到 CSDI 註冊 Token。

**Q2：一定要有 OpenAI API Key 嗎？**
A：唔使。無 Key 時 GenAI 會自動用規則式回應，功能正常，只係無咁「自然」。

**Q3：Streamlit Cloud 部署後 DB 邊度？**
A：因為 `/mount/src/` 係唯讀，DB 同模型必須放 `/tmp/`。App 啟動時會自動初始化 `/tmp/smart_parking.db`。

**Q4：數據幾耐更新一次？**
A：政府實時 API 大約每 5–15 分鐘更新。本項目 GitHub Actions 每小時同步，App 內每 10 分鐘刷新。

**Q5：可以預測幾耐之後？**
A：目前支援未來 30 同 60 分鐘預測。模型基於 30 天歷史數據訓練，預測愈遠誤差愈大。

**Q6：點解淨係得私家車數據？**
A：政府 API 主要提供私家車實時空位。貨車、電單車數據覆蓋率較低，本項目聚焦私家車場景。

**Q7：咪錶數據點解有時缺失？**
A：部分舊式咪錶無實時傳感器，我哋用同街道空間插值估算，會標註「估計」字樣。

---

## ⚠️ 免責聲明

1. **數據來源**：本項目數據來自香港政府數據一站通（data.gov.hk）、運輸署及香港天文台開放數據，僅供學術與教學用途。
2. **預測僅供參考**：空位預測基於歷史數據與機器學習模型，**實際情況可能因突發事件（交通事故、大型活動、惡劣天氣）而偏離預測**。
3. **收費資訊**：停車場收費可能隨時調整，本項目顯示之收費僅供參考，**實際收費以停車場現場公佈為準**。
4. **導航功能**：Google Maps / Waze 導航連結由第三方提供，使用時請遵守當地交通規則。
5. **路邊咪錶**：咪錶實時狀態可能有延遲，**泊車前請親自確認咪錶狀態與收費**。
6. **無商業用途**：本項目為 Xccelerate Capstone 學術項目，**不得用於商業營運**。如需商業使用，請自行向相關政府部門申請數據授權。
7. **系統可用性**：本項目依賴第三方 API 與服務，不保證 100% 可用。API 中斷時會自動切換至模擬數據。

---

## 📜 授權條款

本項目僅供學術/教學用途。數據版權屬香港特區政府，使用請遵守[香港政府開放數據使用條款](https://data.gov.hk/en/terms-and-conditions)。

---

## 📞 聯絡

- **項目**：泊得好 Park Smart HK
- **課程**：Xccelerate Data Science & AI Bootcamp
- **GitHub**：https://github.com/your-username/hongkong-smart-parking

> 「邊度好泊車？泊得好話你知！」 🅿️

---

*最後更新：2026-10-19 ｜ 版本：v1.0.0*
