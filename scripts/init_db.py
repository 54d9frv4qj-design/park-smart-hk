# -*- coding: utf-8 -*-
"""建立資料庫 Schema（無模擬數據）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_engine, init_db

if __name__ == "__main__":
    init_db(get_engine())
    print("Schema 建立完成")
