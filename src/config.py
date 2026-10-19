# -*- coding: utf-8 -*-
"""全局配置：路徑、API、LLM、地區與顏色。"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

_MOUNT_SRC = Path("/mount/src").exists()
try:
    (DATA_DIR / ".write_test").write_text("t")
    (DATA_DIR / ".write_test").unlink()
    _writable = True
except (PermissionError, OSError):
    _writable = False
STREAMLIT_CLOUD = os.getenv("STREAMLIT_CLOUD", "").lower() == "true" or _MOUNT_SRC or not _writable

if STREAMLIT_CLOUD:
    DB_PATH = Path(os.getenv("STREAMLIT_CLOUD_DB_PATH", "/tmp/smart_parking.db"))
    DATA_DIR = Path("/tmp/data")
    LOG_DIR = Path("/tmp/logs")
else:
    DB_PATH = DATA_DIR / "smart_parking.db"

for d in (DATA_DIR, LOG_DIR):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        pass

_db_url = os.getenv("DATABASE_URL", "")
DATABASE_URL = _db_url if _db_url.startswith(("sqlite", "postgresql")) else f"sqlite:///{DB_PATH}"

# 政府 API
DATA_GOV_HK_BASE = os.getenv("DATA_GOV_HK_BASE", "https://api.data.gov.hk/v1")
CARPARK_BASIC_URL = f"{DATA_GOV_HK_BASE}/carpark-info-vacancy?data=basic"
CARPARK_VACANCY_URL = (
    f"{DATA_GOV_HK_BASE}/carpark-info-vacancy"
    "?data=vacancy&vehicleTypes=privateCar&lang=zh_TW"
)
METER_DISTRIBUTION_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/spaceinfo/parkingspaces.csv"
)
METER_OCCUPANCY_URL = (
    "https://resource.data.one.gov.hk/td/psiparkingspaces/occupancystatus/occupancystatus.csv"
)
HKO_BASE = os.getenv("HKO_BASE", "https://data.weather.gov.hk/weatherAPI/opendata")
HKO_WEATHER_URL = f"{HKO_BASE}/weather.php?dataType=rhrread&lang=tc"

API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_RATE_LIMIT_SECONDS = float(os.getenv("API_RATE_LIMIT_SECONDS", "1.0"))
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/csv, */*",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# GenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-68ff543b3295006c693bf2efb28fb6c24fd0d3a68018b3d73c8fa3086d40c6b0"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or "https://discovery-api.intern-ai.org.cn/v1"
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "Agents-A1"
GENAI_LANGUAGE = os.getenv("GENAI_LANGUAGE", "zh-HK")
GENAI_TEMPERATURE = 0.3
GENAI_MAX_TOKENS = 4000

HK_DISTRICTS = [
    {"name": "中西區", "lat": 22.2855, "lng": 114.1490},
    {"name": "灣仔區", "lat": 22.2780, "lng": 114.1750},
    {"name": "東區", "lat": 22.2860, "lng": 114.2210},
    {"name": "南區", "lat": 22.2470, "lng": 114.1650},
    {"name": "油尖旺區", "lat": 22.3120, "lng": 114.1710},
    {"name": "深水埗區", "lat": 22.3310, "lng": 114.1620},
    {"name": "九龍城區", "lat": 22.3280, "lng": 114.1900},
    {"name": "黃大仙區", "lat": 22.3420, "lng": 114.1980},
    {"name": "觀塘區", "lat": 22.3130, "lng": 114.2260},
    {"name": "葵青區", "lat": 22.3570, "lng": 114.1310},
    {"name": "荃灣區", "lat": 22.3710, "lng": 114.1150},
    {"name": "屯門區", "lat": 22.3910, "lng": 113.9770},
    {"name": "元朗區", "lat": 22.4450, "lng": 114.0220},
    {"name": "北區", "lat": 22.4930, "lng": 114.1390},
    {"name": "大埔區", "lat": 22.4510, "lng": 114.1710},
    {"name": "沙田區", "lat": 22.3830, "lng": 114.1900},
    {"name": "西貢區", "lat": 22.3810, "lng": 114.2700},
    {"name": "離島區", "lat": 22.2820, "lng": 113.9450},
]

COLORS = {
    "primary": "#1B3A5C",
    "accent": "#00A8B5",
    "background": "#FFFFFF",
    "secondary_bg": "#F0F4F8",
    "text": "#1B3A5C",
    "green": "#2ECC71",
    "yellow": "#F1C40F",
    "red": "#E74C3C",
    "status_green": "#2ECC71",
    "status_yellow": "#F1C40F",
    "status_red": "#E74C3C",
    "palette": ["#1B3A5C", "#00A8B5", "#2ECC71", "#F1C40F", "#E74C3C", "#9B59B6"],
}
STATUS_THRESHOLDS = {"green": 0.30, "yellow": 0.10}

APP_NAME = os.getenv("APP_NAME", "泊得好 Park Smart HK")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
