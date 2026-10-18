# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — 資料庫連接管理
支援 SQLite（開發）與 PostgreSQL（生產），自動切換
"""
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL, DB_PATH, PROJECT_ROOT


def get_engine() -> Engine:
    """
    建立資料庫 Engine。
    - SQLite：本地開發，自動建立檔案
    - PostgreSQL：生產環境，使用連接池
    """
    if DATABASE_URL.startswith("sqlite"):
        # SQLite：確保目錄存在
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL：連接池配置
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )
    return engine


def init_db(engine: Engine) -> None:
    """執行 schema.sql 初始化資料庫表結構"""
    schema_path = PROJECT_ROOT / "src" / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # SQLite 不支援部分 PostgreSQL 語法，需過濾 TimescaleDB 相關語句
    statements = []
    for stmt in schema_sql.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        # 跳過 TimescaleDB 專用語句（註釋中的）
        if stmt.startswith("-- SELECT create_hypertable"):
            continue
        statements.append(stmt)

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                # 視圖重複建立等錯誤可忽略
                if "already exists" not in str(e).lower():
                    print(f"[DB] 執行 SQL 警告：{e}")
        conn.commit()


def get_connection(engine: Engine):
    """取得資料庫連接（上下文管理器友好）"""
    return engine.connect()


def table_exists(engine: Engine, table_name: str) -> bool:
    """檢查表是否存在"""
    if DATABASE_URL.startswith("sqlite"):
        query = text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        )
    else:
        query = text(
            "SELECT tablename FROM pg_tables WHERE tablename=:name"
        )
    with engine.connect() as conn:
        result = conn.execute(query, {"name": table_name}).fetchone()
    return result is not None
