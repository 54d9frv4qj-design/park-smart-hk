# 🔗 泊得好 Park Smart HK — 網站與現有項目整合方式文檔

## 1. 整合概述

本公眾網站（Streamlit 8 頁 + FastAPI 9 端點）與現有數據管線、機器學習模型、生成式 AI 引擎深度整合。本文檔說明各層級的整合方式。

## 2. 架構整合

```
現有項目（數據管線 + ML + GenAI）
    │
    ├── 資料庫（SQLite/PostgreSQL）◄── FastAPI 讀取
    │         │
    │         ├── Streamlit 直接讀取（簡單查詢）
    │         └── FastAPI 讀取（複雜邏輯 + 預測）
    │
    ├── 機器學習模型（.pkl）◄── FastAPI 載入預測
    │
    └── GenAI 引擎 ◄── FastAPI /chat 端點
              │
              └── Streamlit Chat 頁面呼叫
```

## 3. 資料庫整合

### 連接方式
- **Streamlit**：使用 `src.db.connection.get_engine()` 直接連接
- **FastAPI**：同樣使用 `get_engine()`，共享連接池
- **生產環境**：兩者都連接同一個 PostgreSQL + TimescaleDB

### 資料表共用
| 表 | Streamlit 使用頁面 | FastAPI 端點 |
|----|-------------------|--------------|
| carparks_static | 全部頁面 | map, detail, fees |
| carparks_realtime | 首頁, 地圖, 詳情, 儀表板 | overview, map, detail, dashboard |
| metered_parking | 咪錶頁 | meters |
| meter_occupancy | 咪錶頁 | meters |
| weather_data | 詳情頁, AI對話 | chat |
| carpark_meter_nearby | 詳情頁 | alternatives |
| model_evaluations | 儀表板 | dashboard |

### 視圖共用
- `v_latest_realtime`：每個停車場最新記錄，地圖頁使用
- `v_carpark_status`：靜態+實時 JOIN，列表使用

## 4. 機器學習整合

### 模型載入
```python
# FastAPI 端點中載入模型
import joblib
from src.config import MODEL_DIR

model = joblib.load(MODEL_DIR / "lightgbm_regressor_30min.pkl")
prediction = model.predict(features)
```

### 預測流程
1. 用戶訪問停車場詳情頁
2. Streamlit 呼叫 `/api/detail/{park_id}`
3. FastAPI 從 DB 讀取最新數據
4. 構建特徵（`feature_engineering.py`）
5. 載入 LightGBM 模型預測 30/60 分鐘
6. 返回預測結果給前端顯示

### 模型更新
- 定時任務（每週）執行 `train_all.py` 重新訓練
- 新模型保存到 `models/` 目錄
- FastAPI 下次啟動時載入新模型
- 可熱更新：API 端點呼叫 `reload_models()`

## 5. GenAI 整合

### 對話流程
```
用戶輸入 → Streamlit Chat 頁
    │
    ▼
POST /api/chat
    │
    ▼
query_parser（意圖解析）
    │
    ▼
retriever（從 DB 檢索相關停車場）
    │
    ▼
recommender（加權排序）
    │
    ▼
response_generator（港式繁中回應）
    │
    ▼
返回 Streamlit 顯示
```

### 降級機制
- 無 OpenAI API Key → 使用規則式回應
- DB 查詢失敗 → 返回友好錯誤訊息
- 模型未訓練 → 使用簡單移動平均預測

## 6. ETL 與定時同步整合

### 數據流
```
GitHub Actions（每小時）
    │
    ▼
scripts/sync_realtime.py
    │
    ├── 呼叫政府 API
    ├── ETL 清洗
    ├── 寫入 DB
    └── 失敗時降級模擬數據

Streamlit App（每 10 分鐘）
    │
    ▼
@st.cache_data(ttl=600) 自動刷新
    │
    ▼
從 DB 讀取最新數據
```

### Docker Worker（生產）
- `docker-compose.yml` 中的 worker 服務
- 使用 APScheduler 每 10 分鐘執行同步
- 日誌寫入 `logs/` 目錄

## 7. 前端組件整合

### 共用可視化組件
所有 Streamlit 頁面共用 `src/visualization/` 模組：

| 組件 | 模組 | 使用頁面 |
|------|------|----------|
| Folium 地圖 | maps.py | 首頁, 地圖, 詳情, 咪錶 |
| 7×24 熱力圖 | heatmaps.py | 詳情, 儀表板 |
| 統計卡 | charts.py | 首頁, 儀表板 |
| 趨勢圖 | heatmaps.py | 詳情, 儀表板 |
| 收費比較圖 | heatmaps.py | 收費比較 |
| 咪錶對比圖 | charts.py | 咪錶 |

### 共用配置
- `src/config.py`：顏色主題、API URL、路徑
- `.streamlit/config.toml`：Streamlit 主題
- 所有頁面統一使用 `COLORS` 變數

## 8. API 整合矩陣

| Streamlit 頁面 | API 端點 | 用途 |
|----------------|----------|------|
| 首頁 | GET /api/overview | 統計卡 |
| 首頁 | GET /api/map | 地圖數據 |
| 首頁 | GET /api/search | 搜尋 |
| 實時地圖 | GET /api/map | 地圖數據 |
| 實時地圖 | GET /api/meters | 咪錶疊加 |
| 停車場詳情 | GET /api/detail | 詳情+預測 |
| 停車場詳情 | GET /api/alternatives | 替代推薦 |
| AI 對話 | POST /api/chat | 對話 |
| 路邊咪錶 | GET /api/meters | 咪錶列表 |
| 儀表板 | GET /api/dashboard | 全部儀表板數據 |
| 收費比較 | GET /api/fees | 收費數據 |

## 9. 部署整合

### Streamlit Cloud
- DB 路徑：`/tmp/smart_parking.db`（因 /mount/src/ 唯讀）
- 模型路徑：`/tmp/models/`
- 啟動時自動初始化 DB + 模擬數據
- Secrets 設定 `DATABASE_URL` 和 `OPENAI_API_KEY`

### Docker Compose
- 三容器：api + worker + db
- API 容器暴露 8000 端口
- Worker 容器定時同步
- DB 容器持久化數據卷

### 前後端分離部署
- Streamlit Cloud 前端 → 呼叫 Render FastAPI 後端
- 環境變數 `API_BASE_URL` 指向後端
- CORS 已設定允許所有來源

## 10. 測試整合

### 單元測試
- `tests/test_etl.py`：ETL 管線
- `tests/test_models.py`：機器學習模型

### 整合測試
- `tests/test_api_smoke.py`：FastAPI 9 端點
- `tests/test_streamlit_smoke.py`：Streamlit 8 頁 AppTest

### CI/CD
- `.github/workflows/ci.yml`：Push 時自動測試
- `.github/workflows/sync_data.yml`：每小時數據同步

## 11. 擴展整合點

未來可擴展的整合：
- [ ] 推送通知（泊車位到預測值時通知）
- [ ] 用戶偏好（常用停車場、預設地區）
- [ ] 收藏夾（收藏停車場）
- [ ] 歷史記錄（用戶查詢歷史）
- [ ] 多語言支援（英文/簡體中文）
- [ ] PWA 手機應用
- [ ] Apple CarPlay / Android Auto 整合
