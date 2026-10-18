# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — FastAPI 後端入口
9 個端點：overview, map, detail, alternatives, meters, dashboard, search, chat, fees
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import APP_NAME, APP_VERSION
from src.db.connection import get_engine, init_db
from src.api.routes import (
    overview, map, detail, alternatives,
    meters, dashboard, search, chat, fees,
)
from src.utils.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用啟動/關閉生命週期"""
    log.info(f"🚀 {APP_NAME} v{APP_VERSION} 啟動中...")
    # 初始化資料庫
    engine = get_engine()
    init_db(engine)
    log.info("✅ 資料庫初始化完成")
    yield
    log.info("👋 應用關閉")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="香港智能停車：基於時間序列與多源數據的停車場空位預測與推薦系統",
    lifespan=lifespan,
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(overview.router, prefix="/api", tags=["總覽"])
app.include_router(map.router, prefix="/api", tags=["地圖"])
app.include_router(detail.router, prefix="/api", tags=["停車場詳情"])
app.include_router(alternatives.router, prefix="/api", tags=["替代推薦"])
app.include_router(meters.router, prefix="/api", tags=["路邊咪錶"])
app.include_router(dashboard.router, prefix="/api", tags=["儀表板"])
app.include_router(search.router, prefix="/api", tags=["搜尋"])
app.include_router(chat.router, prefix="/api", tags=["AI 對話"])
app.include_router(fees.router, prefix="/api", tags=["收費比較"])


@app.get("/", tags=["根"])
async def root():
    """根路徑：應用資訊"""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/api/overview", "/api/map", "/api/detail/{park_id}",
            "/api/alternatives/{park_id}", "/api/meters", "/api/dashboard",
            "/api/search", "/api/chat", "/api/fees",
        ],
    }


@app.get("/health", tags=["健康檢查"])
async def health():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": __import__("datetime").datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
