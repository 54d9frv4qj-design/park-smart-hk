-- ============================================================
-- 泊得好 Park Smart HK — SQL 資料庫 Schema
-- 相容 SQLite（開發）與 PostgreSQL + TimescaleDB（生產）
-- ============================================================

-- 啟用外鍵約束（SQLite）
PRAGMA foreign_keys = ON;

-- ============================================================
-- 表 1：停車場基本資料（靜態）
-- ============================================================
CREATE TABLE IF NOT EXISTS carparks_static (
    park_id         TEXT PRIMARY KEY,              -- 停車場編號（如 "1001"）
    name            TEXT NOT NULL,                 -- 停車場名稱
    name_en         TEXT,                          -- 英文名稱
    district        TEXT NOT NULL,                 -- 所屬 18 區
    address         TEXT,                          -- 地址
    lat             REAL NOT NULL,                 -- 緯度（WGS84）
    lng             REAL NOT NULL,                 -- 經度（WGS84）
    total_spaces    INTEGER DEFAULT 0,             -- 私家車總車位
    ev_spaces       INTEGER DEFAULT 0,             -- 電動車位
    motorcycle_spaces INTEGER DEFAULT 0,           -- 電單車位
    goods_vehicle_spaces INTEGER DEFAULT 0,        -- 貨車位
    is_government   INTEGER DEFAULT 0,             -- 是否政府停車場（1=是）
    has_ev_charging INTEGER DEFAULT 0,             -- 有 EV 充電（1=是）
    has_covered     INTEGER DEFAULT 1,             -- 有蓋（1=是）
    hourly_fee      REAL,                          -- 時租（HKD）
    daily_fee       REAL,                          -- 日租（HKD）
    monthly_fee     REAL,                          -- 月票（HKD）
    night_fee       REAL,                          -- 夜泊（HKD）
    fee_estimated   INTEGER DEFAULT 0,             -- 收費是否估計（1=估計）
    operator        TEXT,                          -- 營運商
    contact_phone   TEXT,                          -- 聯絡電話
    opening_hours   TEXT,                          -- 開放時間
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 表 2：停車場實時空位（時間序列，Hypertable in TimescaleDB）
-- ============================================================
CREATE TABLE IF NOT EXISTS carparks_realtime (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id         TEXT NOT NULL,                 -- 停車場編號
    snapshot_time   TEXT NOT NULL,                 -- 快照時間（ISO 8601, HKT）
    vacancy         INTEGER,                       -- 私家車即時空位
    vacancy_ev      INTEGER,                       -- EV 空位
    vacancy_motorcycle INTEGER,                    -- 電單車空位
    vacancy_goods   INTEGER,                       -- 貨車空位
    occupancy_rate  REAL,                          -- 佔用率（0-1）
    status          TEXT,                          -- 狀態：green/yellow/red/full
    data_source     TEXT DEFAULT 'api',            -- 數據來源：api/mock
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (park_id) REFERENCES carparks_static(park_id)
);

-- 索引：按停車場+時間查詢（最常用）
CREATE INDEX IF NOT EXISTS idx_realtime_park_time
    ON carparks_realtime(park_id, snapshot_time DESC);
-- 索引：按時間查詢（儀表板用）
CREATE INDEX IF NOT EXISTS idx_realtime_time
    ON carparks_realtime(snapshot_time DESC);
-- 索引：按地區查詢（需 JOIN）
CREATE INDEX IF NOT EXISTS idx_static_district
    ON carparks_static(district);

-- ============================================================
-- 表 3：路邊咪錶組
-- ============================================================
CREATE TABLE IF NOT EXISTS metered_parking (
    meter_id        TEXT PRIMARY KEY,              -- 咪錶組編號
    group_name      TEXT,                          -- 組別名稱（街道名）
    street_name     TEXT,                          -- 街道名稱
    district        TEXT NOT NULL,                 -- 所屬 18 區
    lat             REAL NOT NULL,                 -- 緯度
    lng             REAL NOT NULL,                 -- 經度
    total_meters    INTEGER DEFAULT 1,             -- 咪錶數量
    total_spaces    INTEGER DEFAULT 0,             -- 總車位
    hourly_fee      REAL,                          -- 時租（HKD）
    max_duration    INTEGER DEFAULT 120,           -- 最長泊車時間（分鐘）
    payment_methods TEXT,                          -- 支付方式（CSV：八達通,信用卡,APP）
    is_new_meter    INTEGER DEFAULT 1,             -- 是否新咪錶（有實時數據）
    operating_hours TEXT,                          -- 營運時間
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 表 4：咪錶實時佔用（時間序列）
-- ============================================================
CREATE TABLE IF NOT EXISTS meter_occupancy (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_id        TEXT NOT NULL,                 -- 咪錶組編號
    snapshot_time   TEXT NOT NULL,                 -- 快照時間
    vacant_spaces   INTEGER,                       -- 空置車位
    occupied_spaces INTEGER,                       -- 佔用車位
    occupancy_rate  REAL,                          -- 佔用率
    status          TEXT,                          -- 狀態
    is_interpolated INTEGER DEFAULT 0,             -- 是否空間插值估算（1=是）
    data_source     TEXT DEFAULT 'api',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (meter_id) REFERENCES metered_parking(meter_id)
);

CREATE INDEX IF NOT EXISTS idx_meter_occ_time
    ON meter_occupancy(meter_id, snapshot_time DESC);

-- ============================================================
-- 表 5：天氣數據（香港天文台）
-- ============================================================
CREATE TABLE IF NOT EXISTS weather_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time   TEXT NOT NULL,                 -- 觀測時間
    district        TEXT,                          -- 分區（如「港島」）
    temperature     REAL,                          -- 氣溫（°C）
    humidity        REAL,                          -- 濕度（%）
    rainfall        REAL DEFAULT 0,                -- 雨量（mm）
    weather_icon    INTEGER,                       -- 天氣圖示代碼
    weather_desc    TEXT,                          -- 天氣描述
    has_warning     INTEGER DEFAULT 0,             -- 是否有天氣警告
    warning_type    TEXT,                          -- 警告類型
    uv_index        REAL,                          -- 紫外線指數
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_weather_time
    ON weather_data(snapshot_time DESC);

-- ============================================================
-- 表 6：停車場×咪錶空間匹配（預計算，加速查詢）
-- ============================================================
CREATE TABLE IF NOT EXISTS carpark_meter_nearby (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id         TEXT NOT NULL,
    meter_id        TEXT NOT NULL,
    distance_m      REAL NOT NULL,                 -- 距離（米）
    walking_minutes REAL,                          -- 步行分鐘（約 80m/min）
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (park_id) REFERENCES carparks_static(park_id),
    FOREIGN KEY (meter_id) REFERENCES metered_parking(meter_id),
    UNIQUE(park_id, meter_id)
);

CREATE INDEX IF NOT EXISTS idx_nearby_park
    ON carpark_meter_nearby(park_id, distance_m);

-- ============================================================
-- 視圖：最新實時狀態（加速查詢）
-- ============================================================
CREATE VIEW IF NOT EXISTS v_latest_realtime AS
SELECT r.*
FROM carparks_realtime r
INNER JOIN (
    SELECT park_id, MAX(snapshot_time) AS max_time
    FROM carparks_realtime
    GROUP BY park_id
) latest ON r.park_id = latest.park_id AND r.snapshot_time = latest.max_time;

-- 視圖：停車場+最新狀態 JOIN
CREATE VIEW IF NOT EXISTS v_carpark_status AS
SELECT
    s.park_id, s.name, s.district, s.address,
    s.lat, s.lng, s.total_spaces, s.ev_spaces,
    s.hourly_fee, s.daily_fee, s.is_government,
    s.has_ev_charging, s.fee_estimated,
    r.vacancy, r.occupancy_rate, r.status,
    r.snapshot_time
FROM carparks_static s
LEFT JOIN v_latest_realtime r ON s.park_id = r.park_id;
