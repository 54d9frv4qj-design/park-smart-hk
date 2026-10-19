# 泊得好 Park Smart HK

香港智能停車 Streamlit 應用：實時空位、地區地圖、停車場詳情、路邊咪錶、收費比較、AI 對話。全部使用政府公開真實數據，不設模擬數據。

## 運行

```bash
pip install -r requirements.txt
streamlit run streamlit_app/Home.py
```

- Python 3.11–3.14
- 啟動時從 `data/csv_export/*.csv.gz` 恢復 SQLite，無需外部資料庫。

## 數據更新（GitHub Actions）

| Workflow | 頻率 | 動作 |
|---|---|---|
| `raw_api_hourly.yml` | 每小時 10 分 | 抓取政府 API 原始快照存入 `data/raw_csv/` |
| `sync_data.yml` | 每小時 5 分 | 同步實時空位、導出壓縮 CSV 存入 `data/csv_export/` |

數據來源：data.gov.hk 停車場空位、運輸署咪錶、香港天文台。

## 目錄

```
streamlit_app/      多頁面應用入口
src/
  config.py         配置與常數
  app_init.py       CSV 恢復資料庫
  data_fetch/       政府 API 抓取
  db/               Schema 與查詢
  genai/            意圖解析、推薦、LLM 回應
  visualization/    地圖與圖表
scripts/            初始化、同步、導出、抓取腳本
data/               隨 repo 提供的壓縮 CSV 快照
.github/workflows/  CI 與定時同步
```

## 測試

```bash
pip install -r requirements-dev.txt
pytest tests/test_etl.py -v
```

## 備註

空位預測與收費僅供參考，實際以停車場現場公佈為準。數據版權屬香港特區政府。
