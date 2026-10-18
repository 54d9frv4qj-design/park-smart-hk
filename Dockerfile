# ============================================================
# 泊得好 Park Smart HK — Dockerfile
# 多階段建置：精簡最終映像大小
# ============================================================

# --- 階段 1：建置依賴 ---
FROM python:3.10-slim AS builder

WORKDIR /app

# 安裝系統依賴（編譯用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- 階段 2：執行階段 ---
FROM python:3.10-slim

WORKDIR /app

# 安裝執行期系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 從 builder 複製已安裝的套件
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 複製專案程式碼
COPY . .

# 建立必要目錄
RUN mkdir -p /tmp/data /tmp/models /tmp/output /tmp/logs

# 環境變數（生產環境）
ENV DATABASE_URL=postgresql://postgres:postgres@db:5432/park_smart_hk
ENV STREAMLIT_CLOUD_DB_PATH=/tmp/smart_parking.db
ENV STREAMLIT_CLOUD_MODEL_DIR=/tmp/models
ENV PYTHONUNBUFFERED=1

# 暴露 FastAPI 端口
EXPOSE 8000

# 預設啟動 FastAPI
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
