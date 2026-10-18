# ============================================================
# 泊得好 Park Smart HK — Makefile 快捷指令
# 用法：make <target>
# ============================================================

.PHONY: help install init-db etl train eda api streamlit test lint clean docker-build docker-up

# 預設目標
help: ## 顯示所有可用指令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安裝所有依賴
	pip install -r requirements-dev.txt

init-db: ## 初始化 SQLite 資料庫與 Schema
	python scripts/init_db.py

etl: ## 執行 ETL：抓取政府 API → 清洗 → 寫入 DB
	python run_pipeline.py --etl

train: ## 訓練所有模型（Prophet / XGBoost / LightGBM / 多任務）
	python run_pipeline.py --train

eda: ## 產生 EDA 報告與圖表
	python -m src.eda.eda_viz

api: ## 啟動 FastAPI 後端（http://localhost:8000）
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

streamlit: ## 啟動 Streamlit 前端（http://localhost:8501）
	streamlit run streamlit_app/Home.py

test: ## 執行全部測試（API 冒煙 + Streamlit AppTest + 單元測試）
	pytest tests/ -v --tb=short

lint: ## 程式碼品質檢查（black + flake8 + isort）
	black src/ streamlit_app/ tests/ scripts/
	isort src/ streamlit_app/ tests/ scripts/
	flake8 src/ streamlit_app/ tests/ scripts/ --max-line-length=120

clean: ## 清理快取與產物
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/

docker-build: ## 建置 Docker 映像
	docker-compose build

docker-up: ## 啟動 Docker 容器（API + Worker + PostgreSQL）
	docker-compose up -d

docker-down: ## 停止 Docker 容器
	docker-compose down

all: init-db etl train eda ## 一鍵完成：初始化 → ETL → 訓練 → EDA
