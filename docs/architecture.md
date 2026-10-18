# 🏗️ 泊得好 Park Smart HK — 系統架構文檔

## 1. 整體架構

本系統採用**分層架構**，分為數據層、服務層、應用層三層：

```
┌─────────────────────────────────────────────────────┐
│                   應用層 (Presentation)               │
│  Streamlit 8頁  │  FastAPI 9端點  │  公眾網站         │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                   服務層 (Service)                    │
│  ETL管線  │  機器學習  │  GenAI推薦  │  空間匹配      │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                   數據層 (Data)                       │
│  SQLite(開發)  │  PostgreSQL+TimescaleDB(生產)        │
│  8張表  │  視圖  │  索引  │  模擬數據生成器            │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                   數據源 (Sources)                    │
│  政府API  │  運輸署CSV  │  天文台API  │  CSDI         │
└─────────────────────────────────────────────────────┘
```

## 2. 數據流

1. **抓取**：定時任務（GitHub Actions 每小時 + App 內每 10 分鐘）呼叫政府 API
2. **清洗**：ETL 管線統一格式、處理缺失值、空間插值
3. **存儲**：寫入 SQLite/PostgreSQL，建立索引
4. **特徵**：機器學習模組構建時間特徵、滯後特徵、滑動窗口
5. **預測**：Prophet/XGBoost/LightGBM/多任務模型預測未來 30-60 分鐘
6. **推薦**：GenAI 引擎解析用戶查詢，加權排序推薦停車場
7. **展示**：Streamlit 前端 + FastAPI 後端提供服務

## 3. 模組依賴關係

```
config.py ← 所有模組
    │
    ├── db/ ← data_fetch, etl, models, genai, api
    ├── mock_data/ ← db, etl
    ├── data_fetch/ ← etl
    ├── etl/ ← run_pipeline, scripts
    ├── models/ ← api, streamlit
    ├── genai/ ← api, streamlit
    ├── visualization/ ← streamlit
    └── utils/ ← 所有模組
```

## 4. 部署架構

### 開發環境
- SQLite 本地數據庫
- Streamlit 本地運行（localhost:8501）
- FastAPI 本地運行（localhost:8000）

### 生產環境
- PostgreSQL + TimescaleDB（時間序列優化）
- FastAPI 部署於 Render / AWS EC2
- Streamlit 部署於 Streamlit Cloud（DB 路徑用 /tmp/）
- Docker Compose：API + Worker + DB 三容器
- Cloud Run Job：每 10 分鐘同步數據

## 5. 關鍵設計決策

| 決策 | 原因 |
|------|------|
| SQLite 開發 / PostgreSQL 生產 | 開發簡單，生產可擴展 |
| TimescaleDB | 時間序列數據查詢優化，190萬+記錄 |
| 模擬數據生成器 | API 403/限流時確保離線可運行 |
| 多模型並存 | Prophet 處理趨勢，XGBoost/LightGBM 處理特徵，多任務處理跨場 |
| 規則式 GenAI 降級 | 無 OpenAI Key 時仍可運行 |
| Folium + OpenStreetMap | 無需 API Key，免費可用 |
