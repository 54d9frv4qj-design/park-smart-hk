# 🏗️ 泊得好 Park Smart HK — 網站架構文檔

## 1. 頁面流程圖

```
                    ┌──────────┐
                    │  首頁 Home │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ 實時地圖    │ │ 停車場詳情  │ │  AI 對話    │
   │ Real-time  │ │   Detail   │ │   Chat     │
   └─────┬──────┘ └─────┬──────┘ └────────────┘
         │              │
         ▼              ▼
   ┌────────────┐ ┌────────────┐
   │ 路邊咪錶    │ │ 收費比較    │
   │   Meters   │ │   Fees     │
   └────────────┘ └────────────┘

   ┌────────────┐ ┌────────────┐
   │  儀表板     │ │   關於      │
   │ Dashboard  │ │   About    │
   └────────────┘ └────────────┘
```

## 2. 系統架構圖

```
┌──────────────────────────────────────────────────────────┐
│                    使用者瀏覽器                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Streamlit 前端（8 頁）               │    │
│  │  Home │ Map │ Detail │ Chat │ Meters │ Dashboard │    │
│  │         │ Fees │ About                            │    │
│  └─────────────────────┬────────────────────────────┘    │
└────────────────────────┼─────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼─────────────────────────────────┐
│                  FastAPI 後端（9 端點）                    │
│  overview │ map │ detail │ alternatives │ meters          │
│  dashboard │ search │ chat │ fees                        │
└─────────────────────┬───────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ 資料庫    │ │ 機器學習  │ │ GenAI    │
   │ SQLite/  │ │ XGBoost  │ │ RAG      │
   │ Postgres │ │ LightGBM │ │ 港式中文 │
   │          │ │ Prophet  │ │          │
   └──────────┘ └──────────┘ └──────────┘
```

## 3. 數據流圖

```
政府 API ──► ETL 管線 ──► 資料庫 ──► FastAPI ──► Streamlit
   │            │           │          │           │
   │        清洗/正則化    查詢      預測/推薦    渲染
   │            │           │          │           │
   ▼            ▼           ▼          ▼           ▼
模擬數據 ◄── 降級機制   索引優化   模型推理    Folium地圖
生成器                              ECharts圖表
```

## 4. 組件圖

### 前端組件（Streamlit）

| 組件 | 位置 | 功能 |
|------|------|------|
| SearchBar | Home | 搜尋停車場/咪錶 |
| StatsCards | Home, Dashboard | 統計卡 |
| FoliumMap | Home, Map, Detail | 互動地圖 |
| Top5Ranking | Home | 最易泊/最緊張排名 |
| VacancyGauge | Detail | 佔用率儀表盤 |
| ForecastChart | Detail | 預測走勢圖 |
| HistoryChart | Detail | 24h 歷史圖 |
| Heatmap7x24 | Detail, Dashboard | 7×24 熱力圖 |
| ChatInterface | Chat | 對話界面 |
| QuickQuestions | Chat | 快捷問題按鈕 |
| MeterList | Meters | 咪錶列表 |
| FeeTable | Fees | 收費比較表 |

### 後端組件（FastAPI）

| 組件 | 功能 |
|------|------|
| QueryParser | 自然語言意圖解析 |
| Recommender | 加權排序推薦 |
| ResponseGenerator | 港式繁中回應生成 |
| RAGEngine | 檢索增強對話 |
| FeatureEngineer | 特徵構建 |
| ModelRegistry | 模型管理與載入 |
| DBConnection | 資料庫連接池 |
| ETLPipeline | 數據抓取與清洗 |

## 5. 頁面與 API 對應

| 頁面 | 使用的 API 端點 |
|------|-----------------|
| 首頁 | /api/overview, /api/map, /api/search |
| 實時地圖 | /api/map, /api/meters |
| 停車場詳情 | /api/detail, /api/alternatives |
| AI 對話 | /api/chat |
| 路邊咪錶 | /api/meters |
| 儀表板 | /api/dashboard |
| 收費比較 | /api/fees |
| 關於 | 無（靜態內容） |
