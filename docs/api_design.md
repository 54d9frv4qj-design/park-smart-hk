# 🌐 泊得好 Park Smart HK — FastAPI 設計文檔

## API 概覽

- **基礎 URL**：`http://localhost:8000/api`
- **文檔**：`http://localhost:8000/docs`（Swagger UI）
- **格式**：JSON
- **編碼**：UTF-8（繁體中文）

## 端點一覽

| # | 方法 | 端點 | 說明 |
|---|------|------|------|
| 1 | GET | `/api/overview` | 全港統計總覽 |
| 2 | GET | `/api/map` | 地圖數據（所有停車場位置+狀態） |
| 3 | GET | `/api/detail/{park_id}` | 單個停車場詳情 |
| 4 | GET | `/api/alternatives/{park_id}` | 替代停車場推薦 |
| 5 | GET | `/api/meters` | 路邊咪錶列表/地圖數據 |
| 6 | GET | `/api/dashboard` | 儀表板數據 |
| 7 | GET | `/api/search` | 搜尋停車場/咪錶 |
| 8 | POST | `/api/chat` | AI 對話 |
| 9 | GET | `/api/fees` | 收費比較數據 |

## 端點詳情

### 1. GET /api/overview
全港停車場統計總覽。

**響應示例**：
```json
{
  "total_carparks": 607,
  "total_spaces": 85000,
  "avg_occupancy": 0.65,
  "green_count": 280,
  "yellow_count": 200,
  "red_count": 127,
  "total_meters": 200,
  "update_time": "2026-10-19 14:30:00"
}
```

### 2. GET /api/map
取得所有停車場地圖數據。

**參數**：
- `district`（可選）：按地區篩選
- `vehicle_type`（可選）：車型，預設 `privateCar`

**響應示例**：
```json
{
  "points": [
    {
      "park_id": "1001",
      "name": "中環天星碼頭停車場",
      "district": "中西區",
      "lat": 22.2855,
      "lng": 114.1610,
      "vacancy": 35,
      "total_spaces": 120,
      "occupancy_rate": 0.71,
      "status": "yellow",
      "hourly_fee": 30
    }
  ],
  "count": 607
}
```

### 3. GET /api/detail/{park_id}
取得單個停車場詳情，含實時狀態與預測。

**響應示例**：
```json
{
  "park_id": "1001",
  "name": "中環天星碼頭停車場",
  "district": "中西區",
  "lat": 22.2855,
  "lng": 114.1610,
  "total_spaces": 120,
  "vacancy": 35,
  "occupancy_rate": 0.71,
  "status": "yellow",
  "hourly_fee": 30,
  "prediction_30min": 33,
  "prediction_60min": 30,
  "update_time": "2026-10-19 14:30:00"
}
```

### 4. GET /api/alternatives/{park_id}
取得目標停車場附近的替代停車場。

**參數**：
- `radius_km`（可選）：搜尋半徑，預設 1.0
- `limit`（可選）：返回數量，預設 5

### 5. GET /api/meters
取得路邊咪錶實時狀態。

**參數**：
- `district`（可選）：按地區篩選
- `status`（可選）：按狀態篩選
- `limit`（可選）：返回數量，預設 200

### 6. GET /api/dashboard
取得儀表板數據（統計+排名+熱力圖+趨勢）。

**參數**：
- `days`（可選）：趨勢天數，預設 14

### 7. GET /api/search
搜尋停車場。

**參數**：
- `q`：搜尋關鍵字
- `district`（可選）：地區
- `vehicle_type`（可選）：車型
- `limit`（可選）：返回數量

### 8. POST /api/chat
AI 對話：自然語言查詢停車場建議。

**請求體**：
```json
{
  "message": "而家旺角邊度有位泊？",
  "history": [{"role": "user", "content": "你好"}]
}
```

**響應示例**：
```json
{
  "response": "旺角最易泊嘅停車場：\n1. 新世紀廣場...",
  "intent": "find_parking",
  "confidence": 0.85,
  "recommendations": [...],
  "response_time_ms": 120.5
}
```

### 9. GET /api/fees
取得停車場收費比較數據。

**參數**：
- `district`（可選）：按地區篩選
- `sort_by`（可選）：排序欄位，預設 `hourly_fee`
- `limit`（可選）：返回數量

## 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功 |
| 404 | 停車場/咪錶唔存在 |
| 422 | 請求參數錯誤 |
| 500 | 伺服器錯誤 |

## 錯誤響應格式

```json
{
  "detail": "停車場 NONEXISTENT 唔存在"
}
```
