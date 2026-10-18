# 📖 泊得好 Park Smart HK — 數據字典

## 表 1：carparks_static（停車場基本資料）

| 欄位 | 類型 | 說明 | 示例 |
|------|------|------|------|
| park_id | TEXT PK | 停車場編號 | "1001" |
| name | TEXT | 中文名稱 | "中環天星碼頭停車場" |
| name_en | TEXT | 英文名稱 | "Central Star Ferry Car Park" |
| district | TEXT | 所屬 18 區 | "中西區" |
| address | TEXT | 地址 | "中環民光街" |
| lat | REAL | 緯度（WGS84） | 22.2855 |
| lng | REAL | 經度（WGS84） | 114.1610 |
| total_spaces | INTEGER | 私家車總車位 | 120 |
| ev_spaces | INTEGER | 電動車位 | 10 |
| motorcycle_spaces | INTEGER | 電單車位 | 5 |
| goods_vehicle_spaces | INTEGER | 貨車位 | 0 |
| is_government | INTEGER | 是否政府停車場（1=是） | 1 |
| has_ev_charging | INTEGER | 有 EV 充電 | 1 |
| has_covered | INTEGER | 有蓋 | 1 |
| hourly_fee | REAL | 時租（HKD） | 30 |
| daily_fee | REAL | 日租（HKD） | 300 |
| monthly_fee | REAL | 月票（HKD） | 4500 |
| night_fee | REAL | 夜泊（HKD） | 150 |
| fee_estimated | INTEGER | 收費是否估計（1=估計） | 0 |
| operator | TEXT | 營運商 | "政府" |
| contact_phone | TEXT | 聯絡電話 | "21234567" |
| opening_hours | TEXT | 開放時間 | "24小時" |
| created_at | TEXT | 建立時間 | "2026-10-19 14:00:00" |
| updated_at | TEXT | 更新時間 | "2026-10-19 14:00:00" |

## 表 2：carparks_realtime（停車場實時空位，時間序列）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| park_id | TEXT FK | 停車場編號 |
| snapshot_time | TEXT | 快照時間（ISO 8601） |
| vacancy | INTEGER | 私家車即時空位 |
| vacancy_ev | INTEGER | EV 空位 |
| vacancy_motorcycle | INTEGER | 電單車空位 |
| vacancy_goods | INTEGER | 貨車空位 |
| occupancy_rate | REAL | 佔用率（0-1） |
| status | TEXT | 狀態：green/yellow/red/full |
| data_source | TEXT | 數據來源：api/mock |
| created_at | TEXT | 建立時間 |

**索引**：
- `idx_realtime_park_time` (park_id, snapshot_time DESC)
- `idx_realtime_time` (snapshot_time DESC)

## 表 3：metered_parking（路邊咪錶組）

| 欄位 | 類型 | 說明 |
|------|------|------|
| meter_id | TEXT PK | 咪錶組編號 |
| group_name | TEXT | 組別名稱 |
| street_name | TEXT | 街道名稱 |
| district | TEXT | 所屬 18 區 |
| lat | REAL | 緯度 |
| lng | REAL | 經度 |
| total_meters | INTEGER | 咪錶數量 |
| total_spaces | INTEGER | 總車位 |
| hourly_fee | REAL | 時租（HKD） |
| max_duration | INTEGER | 最長泊車時間（分鐘） |
| payment_methods | TEXT | 支付方式（CSV） |
| is_new_meter | INTEGER | 是否新咪錶 |
| operating_hours | TEXT | 營運時間 |

## 表 4：meter_occupancy（咪錶實時佔用，時間序列）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| meter_id | TEXT FK | 咪錶組編號 |
| snapshot_time | TEXT | 快照時間 |
| vacant_spaces | INTEGER | 空置車位 |
| occupied_spaces | INTEGER | 佔用車位 |
| occupancy_rate | REAL | 佔用率 |
| status | TEXT | 狀態 |
| is_interpolated | INTEGER | 是否空間插值估算 |
| data_source | TEXT | 數據來源 |

## 表 5：weather_data（天氣數據）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| snapshot_time | TEXT | 觀測時間 |
| district | TEXT | 分區 |
| temperature | REAL | 氣溫（°C） |
| humidity | REAL | 濕度（%） |
| rainfall | REAL | 雨量（mm） |
| weather_icon | INTEGER | 天氣圖示代碼 |
| weather_desc | TEXT | 天氣描述 |
| has_warning | INTEGER | 是否有天氣警告 |
| warning_type | TEXT | 警告類型 |
| uv_index | REAL | 紫外線指數 |

## 表 6：carpark_meter_nearby（停車場×咪錶空間匹配）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| park_id | TEXT FK | 停車場編號 |
| meter_id | TEXT FK | 咪錶組編號 |
| distance_m | REAL | 距離（米） |
| walking_minutes | REAL | 步行分鐘 |

## 表 7：model_evaluations（模型評估記錄）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| model_name | TEXT | 模型名稱 |
| forecast_horizon | INTEGER | 預測範圍（分鐘） |
| metric_name | TEXT | 指標名稱 |
| metric_value | REAL | 指標值 |
| train_samples | INTEGER | 訓練樣本數 |
| test_samples | INTEGER | 測試樣本數 |
| evaluated_at | TEXT | 評估時間 |
| details | TEXT | JSON 詳情 |

## 表 8：chat_logs（AI 對話日誌）

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| session_id | TEXT | 會話 ID |
| user_message | TEXT | 用戶訊息 |
| ai_response | TEXT | AI 回應 |
| intent | TEXT | 解析意圖 |
| recommended_park | TEXT | 推薦停車場 |
| response_time_ms | REAL | 回應耗時 |
| created_at | TEXT | 建立時間 |

## 視圖

### v_latest_realtime
每個停車場最新一筆實時記錄。

### v_carpark_status
停車場基本資料 + 最新狀態 JOIN，用於地圖與列表。

## 狀態編碼

| status | 顏色 | 條件 | 中文 |
|--------|------|------|------|
| green | 🟢 綠 | 空位率 > 30% | 充足 |
| yellow | 🟡 黃 | 空位率 10-30% | 偏緊 |
| red | 🔴 紅 | 空位率 < 10% | 緊張 |
| full | 🔴 紅 | 空位 = 0 | 滿座 |
| unknown | ⚪ 灰 | 無數據 | 未知 |
