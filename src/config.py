# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 全局配置
所有 URL、路徑、常數、顏色主題集中管理
"""
import os
from pathlib import Path

# 選擇性載入 .env（python-dotenv 未安裝時跳過）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================================
# 路徑配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

# 自動偵測 Streamlit Cloud 環境
# Streamlit Cloud：程式碼在 /mount/src/（唯讀），所有可寫檔案必須放 /tmp/
_STREAMLIT_CLOUD_ENV = os.getenv("STREAMLIT_CLOUD", "").lower() == "true"
_MOUNT_SRC_EXISTS = Path("/mount/src").exists()
# 檢查項目 data 目錄是否可寫（唔可寫就當係 Streamlit Cloud）
try:
    _test_file = DATA_DIR / ".write_test"
    _test_file.write_text("test")
    _test_file.unlink()
    _data_dir_writable = True
except (PermissionError, OSError):
    _data_dir_writable = False
STREAMLIT_CLOUD = _STREAMLIT_CLOUD_ENV or _MOUNT_SRC_EXISTS or not _data_dir_writable

if STREAMLIT_CLOUD:
    # Streamlit Cloud：/mount/src/ 唯讀，所有可寫檔案放 /tmp/
    DB_PATH = Path(os.getenv("STREAMLIT_CLOUD_DB_PATH", "/tmp/smart_parking.db"))
    MODEL_DIR = Path(os.getenv("STREAMLIT_CLOUD_MODEL_DIR", "/tmp/models"))
    DATA_DIR = Path("/tmp/data")
    OUTPUT_DIR = Path("/tmp/output")
    LOG_DIR = Path("/tmp/logs")
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
else:
    DB_PATH = DATA_DIR / "smart_parking.db"

# 確保目錄存在（僅在可寫入環境）
for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODEL_DIR, OUTPUT_DIR, LOG_DIR]:
    try:
        d.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        pass

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ============================================================
# 政府 API 配置
# ============================================================
DATA_GOV_HK_BASE = os.getenv("DATA_GOV_HK_BASE", "https://api.data.gov.hk/v1")
CARPARK_BASIC_URL = f"{DATA_GOV_HK_BASE}/carpark-info-vacancy?data=basic"
CARPARK_VACANCY_URL = (
    f"{DATA_GOV_HK_BASE}/carpark-info-vacancy"
    "?data=vacancy&vehicleTypes=privateCar&lang=zh_TW"
)

# 運輸署咪錶數據（備用公開端點）
METER_DISTRIBUTION_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/"
    "spaceinfo/parkingspaces.csv"
)
METER_OCCUPANCY_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/"
    "occupancystatus/occupancystatus.csv"
)

# CSDI（需 Token，可選）
CSDI_TOKEN = os.getenv("CSDI_TOKEN", "")
CSDI_METER_URL = (
    "https://portal.csdi.gov.hk/geospatial/rest/services/common/"
    "tdd_parking_meter/FeatureServer/0/query"
)

# 香港天文台
HKO_BASE = os.getenv("HKO_BASE", "https://data.weather.gov.hk/weatherAPI/opendata")
HKO_WEATHER_URL = f"{HKO_BASE}/weather.php?dataType=rhrread&lang=tc"
HKO_WARNING_URL = f"{HKO_BASE}/weather.php?dataType=warnsum&lang=tc"

# API 請求設定
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_RATE_LIMIT_SECONDS = float(os.getenv("API_RATE_LIMIT_SECONDS", "1.0"))
API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/csv, */*",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# ============================================================
# 生成式 AI 配置
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-68ff543b3295006c693bf2efb28fb6c24fd0d3a68018b3d73c8fa3086d40c6b0")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://discovery-api.intern-ai.org.cn/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GENAI_LANGUAGE = os.getenv("GENAI_LANGUAGE", "zh-HK")
GENAI_TEMPERATURE = 0.7
GENAI_MAX_TOKENS = 500

# ============================================================
# 模擬數據配置
# ============================================================
MOCK_CARPARK_COUNT = int(os.getenv("MOCK_CARPARK_COUNT", "607"))
MOCK_METER_COUNT = int(os.getenv("MOCK_METER_COUNT", "200"))
MOCK_HISTORY_DAYS = int(os.getenv("MOCK_HISTORY_DAYS", "30"))
MOCK_INTERVAL_MINUTES = 15  # 每 15 分鐘一筆

# ============================================================
# 香港 18 區配置（含中心經緯度，用於模擬數據分佈）
# ============================================================
HK_DISTRICTS = [
    {"name": "中西區", "lat": 22.2855, "lng": 114.1490, "density": 0.95},
    {"name": "灣仔區", "lat": 22.2780, "lng": 114.1750, "density": 0.98},
    {"name": "東區", "lat": 22.2860, "lng": 114.2210, "density": 0.75},
    {"name": "南區", "lat": 22.2470, "lng": 114.1650, "density": 0.55},
    {"name": "油尖旺區", "lat": 22.3120, "lng": 114.1710, "density": 1.00},
    {"name": "深水埗區", "lat": 22.3310, "lng": 114.1620, "density": 0.85},
    {"name": "九龍城區", "lat": 22.3280, "lng": 114.1900, "density": 0.80},
    {"name": "黃大仙區", "lat": 22.3420, "lng": 114.1980, "density": 0.70},
    {"name": "觀塘區", "lat": 22.3130, "lng": 114.2260, "density": 0.88},
    {"name": "葵青區", "lat": 22.3570, "lng": 114.1310, "density": 0.72},
    {"name": "荃灣區", "lat": 22.3710, "lng": 114.1150, "density": 0.68},
    {"name": "屯門區", "lat": 22.3910, "lng": 113.9770, "density": 0.60},
    {"name": "元朗區", "lat": 22.4450, "lng": 114.0220, "density": 0.58},
    {"name": "北區", "lat": 22.4930, "lng": 114.1390, "density": 0.45},
    {"name": "大埔區", "lat": 22.4510, "lng": 114.1710, "density": 0.50},
    {"name": "沙田區", "lat": 22.3830, "lng": 114.1900, "density": 0.78},
    {"name": "西貢區", "lat": 22.3810, "lng": 114.2700, "density": 0.40},
    {"name": "離島區", "lat": 22.2820, "lng": 113.9450, "density": 0.35},
]

# ============================================================
# 顏色主題（深藍 + 青 + 狀態色）
# ============================================================
COLORS = {
    "primary": "#1B3A5C",        # 深藍
    "accent": "#00A8B5",         # 青
    "background": "#FFFFFF",
    "secondary_bg": "#F0F4F8",
    "text": "#1B3A5C",
    # 停車場狀態色（簡寫）
    "green": "#2ECC71",          # 空位充足 >30%
    "yellow": "#F1C40F",         # 偏緊 10-30%
    "red": "#E74C3C",            # 滿座 <10%
    # 停車場狀態色（全名，相容舊代碼）
    "status_green": "#2ECC71",
    "status_yellow": "#F1C40F",
    "status_red": "#E74C3C",
    # 圖表調色板
    "palette": ["#1B3A5C", "#00A8B5", "#2ECC71", "#F1C40F", "#E74C3C", "#9B59B6"],
}

# 狀態閾值
STATUS_THRESHOLDS = {
    "green": 0.30,   # >30% 空位 → 綠
    "yellow": 0.10,  # 10-30% → 黃，<10% → 紅
}

# ============================================================
# 收費配置（26 個政府場真實收費 + 581 個估計）
# ============================================================
GOVERNMENT_CARPARTS = 26  # 政府停車場數量（有真實收費）
ESTIMATED_CARPARTS = 581  # 其餘估計收費
TOTAL_CARPARTS = 607

# 典型收費範圍（港幣）
FEE_RANGES = {
    "hourly": (15, 55),
    "daily": (150, 400),
    "monthly": (3000, 6500),
    "night": (100, 250),  # 夜泊（通常 8PM-8AM）
}

# ============================================================
# 應用配置
# ============================================================
APP_NAME = os.getenv("APP_NAME", "泊得好 Park Smart HK")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "10"))

# 預測範圍
FORECAST_HORIZONS = [30, 60]  # 分鐘
