# 🚀 泊得好 Park Smart HK — 部署指南

## 方案一：Streamlit Cloud（推薦，免費）

### 優點
- 免費、自動 HTTPS、GitHub 一鍵部署
- 適合展示與演示

### 限制
- `/mount/src/` 唯讀，DB 同模型必須放 `/tmp/`
- 記憶體上限 1GB
- 閒置後會休眠

### 部署步驟

1. **Push 到 GitHub**
```bash
git init
git add .
git commit -m "Initial commit: 泊得好 Park Smart HK"
git branch -M main
git remote add origin https://github.com/your-username/hongkong-smart-parking.git
git push -u origin main
```

2. **到 Streamlit Cloud 部署**
   - 前往 <https://share.streamlit.io>
   - 用 GitHub 帳號登入
   - 點 **New app**
   - Repository：`your-username/hongkong-smart-parking`
   - Branch：`main`
   - Main file path：`streamlit_app/Home.py`

3. **設定 Secrets**（Settings → Secrets）
```toml
DATABASE_URL = "sqlite:////tmp/smart_parking.db"
OPENAI_API_KEY = "sk-..."  # 可選
```

4. **高級設定**
   - Python version：3.11
   - 點 **Deploy!**

### 成本
- **免費**（開源專案）

---

## 方案二：Render（後端+前端分離）

### 優點
- 支援 FastAPI + PostgreSQL
- 自動 HTTPS、自動部署
- 免費層可用

### 部署步驟

1. **Web Service（FastAPI）**
   - New → Web Service
   - 連接 GitHub 倉庫
   - Runtime：Docker
   - Dockerfile Path：`./Dockerfile`
   - 環境變數：`DATABASE_URL`、`OPENAI_API_KEY`
   - Instance Type：Starter $7/月

2. **PostgreSQL**
   - New → PostgreSQL
   - Name：`park-smart-hk-db`
   - Version：15
   - Instance：Free $0/月 或 Starter $7/月

3. **Streamlit 前端**
   - 獨立部署到 Streamlit Cloud（方案一）
   - API URL 指向 Render Web Service

### 成本估算
| 資源 | 規格 | 月費 |
|------|------|------|
| FastAPI Web Service | Starter 512MB | $7 |
| PostgreSQL | Starter 1GB | $7 |
| Streamlit Cloud | Free | $0 |
| **合計** | | **~$14/月** |

---

## 方案三：AWS EC2（完全控制）

### 優點
- 完全控制、可跑 PostgreSQL + TimescaleDB + Worker
- 適合生產環境

### 部署步驟

1. **啟動 EC2 實例**
   - AMI：Ubuntu 22.04 LTS
   - 類型：t3.micro（免費層）或 t3.small
   - 儲存：30GB gp3
   - 安全組：開放 22(SSH), 80(HTTP), 443(HTTPS), 8000(FastAPI), 8501(Streamlit)

2. **安裝 Docker**
```bash
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
```

3. **部署應用**
```bash
git clone https://github.com/your-username/hongkong-smart-parking.git
cd hongkong-smart-parking
docker-compose up -d
```

4. **設定 Nginx 反向代理 + SSL**
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

5. **設定定時同步**
```bash
# 每 10 分鐘同步
*/10 * * * * cd /home/ubuntu/hongkong-smart-parking && docker-compose exec worker python scripts/sync_realtime.py
```

### 成本估算
| 資源 | 規格 | 月費 |
|------|------|------|
| EC2 | t3.small | $15 |
| EBS | 30GB gp3 | $3 |
| 數據傳輸 | 100GB | $9 |
| **合計** | | **~$27/月** |

---

## 定時同步配置

### GitHub Actions（每小時）
已配置 `.github/workflows/sync_data.yml`，每小時第 5 分鐘自動執行。

### App 內刷新（每 10 分鐘）
Streamlit 使用 `@st.cache_data(ttl=600)` 自動刷新。

### Docker Worker（生產）
`docker-compose.yml` 中的 worker 服務使用 APScheduler 每 10 分鐘同步。

---

## 環境變數清單

| 變數 | 說明 | 必需 |
|------|------|------|
| `DATABASE_URL` | 資料庫連接字串 | ✅ |
| `OPENAI_API_KEY` | OpenAI API Key（可選，無則用規則式） | ❌ |
| `CSDI_TOKEN` | CSDI Token（可選） | ❌ |
| `DEBUG` | 除錯模式 | ❌ |
| `LOG_LEVEL` | 日誌級別 | ❌ |
