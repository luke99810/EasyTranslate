# EasyTranslate 部署指南

> EasyTranslate 是一个学术 PDF 翻译工具，前后端分离架构：前端 React + Vite，后端 Python + FastAPI。本文档涵盖本地开发、Docker、GitHub Pages、Netlify、Vercel 等主流部署方式。

---

## 目录

1. [架构概览](#1-架构概览)
2. [环境要求](#2-环境要求)
3. [本地开发部署](#3-本地开发部署)
4. [Docker 部署](#4-docker-部署)
5. [GitHub 部署（前后端一体）](#5-github-部署前后端一体)
6. [Netlify 前端部署](#6-netlify-前端部署)
7. [Vercel 前端部署](#7-vercel-前端部署)
8. [云服务器部署（生产推荐）](#8-云服务器部署生产推荐)
9. [常见问题](#9-常见问题)

---

## 1. 架构概览

```
EasyTranslate/
├── paper-translate/
│   ├── frontend/          # React 18 + Vite + TailwindCSS
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── package.json
│   ├── backend/           # Python 3.10 + FastAPI
│   │   ├── app/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── docker-compose.yml # 一键编排
├── docs/
├── README.md
└── User Guide.md
```

**端口分配：**

| 服务 | 默认端口 | 说明 |
|------|---------|------|
| 前端（开发） | 3000 | Vite dev server |
| 前端（Docker） | 80 | Nginx 静态托管 |
| 后端 API | 8000 | FastAPI / Uvicorn |

**API 路由前缀：** `/api/`（所有后端接口均以 `/api` 开头）

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/pdf/upload` | 上传 PDF |
| GET | `/api/pdf/{file_id}/info` | 获取 PDF 信息 |
| POST | `/api/translate` | 启动翻译任务 |
| GET | `/api/translate/{task_id}/status` | 查询翻译状态 |
| GET | `/api/translate/{task_id}/result` | 获取翻译结果 |
| POST | `/api/translate/{task_id}/cancel` | 取消翻译 |
| POST | `/api/export/pdf` | 导出 PDF |
| POST | `/api/export/word` | 导出 Word |

---

## 2. 环境要求

### 本地开发

| 依赖 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Node.js | v18.0+ | v20.x LTS |
| Python | v3.10+ | v3.10.x |
| Git | 任意 | 最新 |

### Docker 部署

| 依赖 | 最低版本 |
|------|---------|
| Docker | v20.10+ |
| Docker Compose | v1.29+ / v2.x |

### 云平台部署

- GitHub 账号（GitHub Pages）
- Netlify 账号（前端部署）
- Vercel 账号（前端部署）
- 云服务器（生产部署，推荐 Ubuntu 22.04 LTS）

---

## 3. 本地开发部署

### 3.1 克隆项目

```bash
git clone https://github.com/your-username/EasyTranslate.git
cd EasyTranslate/paper-translate
```

### 3.2 启动后端（终端 1）

```powershell
# 进入后端目录
cd backend

# 创建虚拟环境（Windows）
python -m venv venv
venv\Scripts\activate

# macOS / Linux
# python3 -m venv venv
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
uvicorn app.main:app --reload
```

后端启动后运行在 `http://localhost:8000`，可访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 3.3 启动前端（终端 2）

```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后运行在 `http://localhost:3000`。

Vite 配置了自动代理，前端 `/api/*` 请求会自动转发到 `http://localhost:8000`，无需手动配置跨域。

### 3.4 访问应用

打开浏览器访问 **http://localhost:3000**。

### 3.5 停止服务

在两个终端分别按 `Ctrl+C` 停止前后端服务。

---

## 4. Docker 部署

### 4.1 前提条件

确保 Docker Desktop（Windows/Mac）或 Docker Engine（Linux）已安装并运行。

验证：
```bash
docker --version
docker-compose --version
```

### 4.2 一键启动

```bash
cd paper-translate
docker-compose up -d
```

首次运行会自动构建镜像，预计 3-5 分钟（取决于网络）。

### 4.3 验证服务

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 测试后端健康检查
curl http://localhost:8000/health
```

### 4.4 访问应用

| 入口 | 地址 |
|------|------|
| 前端页面 | http://localhost |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

### 4.5 端口冲突处理

如果 80 端口被占用，修改 `docker-compose.yml` 中的前端端口映射：

```yaml
services:
  frontend:
    ports:
      - "3000:80"  # 改为其他端口
```

然后重新启动：
```bash
docker-compose down
docker-compose up -d
```

### 4.6 常用管理命令

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重新构建并启动
docker-compose up -d --build

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 重启单个服务
docker-compose restart backend
```

### 4.7 数据持久化

Docker Compose 已配置 volume 挂载：

- `./backend/uploads` → 容器内 `/app/uploads`（上传的 PDF）
- `./backend/outputs` → 容器内 `/app/outputs`（翻译结果）

容器重启不会丢失数据。

---

## 5. GitHub 部署（前后端一体）

### 5.1 创建 GitHub 仓库

```bash
# 在项目根目录初始化
cd EasyTranslate
git init
git add .
git commit -m "Initial commit"

# 创建 GitHub 仓库并推送
gh repo create EasyTranslate --public --source=. --push
```

### 5.2 GitHub Actions 自动部署

创建 `.github/workflows/deploy.yml` 实现推送后自动构建 Docker 镜像并部署：

```yaml
name: Deploy to Server

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub (可选)
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./paper-translate
          push: true
          tags: your-dockerhub-user/easytranslate:latest
```

### 5.3 使用 GitHub Container Registry（GHCR）

如果你不想用 Docker Hub，可以用 GitHub 自带的容器仓库：

```bash
# 本地构建并推送
cd paper-translate
docker build -t ghcr.io/your-username/easytranslate:latest .
docker push ghcr.io/your-username/easytranslate:latest
```

> **注意**：GitHub Pages 只能托管静态前端，无法运行 Python 后端。如需完整部署，请参考[第 8 节云服务器部署](#8-云服务器部署生产推荐)。

---

## 6. Netlify 前端部署

> **重要**：Netlify 只能部署静态前端，后端 API 需要单独部署（如 Railway、Render、云服务器）。前端通过环境变量 `VITE_API_URL` 指向后端地址。

### 6.1 配置后端地址

在前端目录创建 `.env.production`：

```bash
VITE_API_URL=https://your-backend-server.com/api
```

### 6.2 构建前端

```bash
cd paper-translate/frontend
npm install
npm run build
```

构建产物在 `dist/` 目录。

### 6.3 方式 A：拖拽部署

1. 打开 [Netlify](https://app.netlify.com/)
2. 将 `paper-translate/frontend/dist` 文件夹**拖拽**到 Netlify 页面
3. 等待部署完成，获取访问 URL

### 6.4 方式 B：Git 连接部署

1. 将项目推送到 GitHub
2. 在 Netlify 点击 **New site from Git**
3. 选择仓库，配置：
   - **Build command**: `npm run build`
   - **Publish directory**: `dist`
   - **Base directory**: `paper-translate/frontend`
4. 添加环境变量：
   - `VITE_API_URL` = `https://your-backend-server.com/api`
5. 点击 **Deploy site**

### 6.5 SPA 路由处理

Netlify 默认已支持 SPA 路由（try_files），无需额外配置。如果出现刷新 404，在 `paper-translate/frontend` 目录创建 `public/_redirects`：

```
/*    /index.html   200
```

---

## 7. Vercel 前端部署

### 7.1 方式 A：Vercel CLI

```bash
# 安装 Vercel CLI
npm i -g vercel

# 在前端目录部署
cd paper-translate/frontend
vercel

# 按提示操作，或使用非交互模式
vercel --prod --yes
```

### 7.2 方式 B：Git 连接部署

1. 将项目推送到 GitHub
2. 打开 [Vercel](https://vercel.com/)，点击 **New Project**
3. 导入 GitHub 仓库
4. 配置：
   - **Framework Preset**: Vite
   - **Root Directory**: `paper-translate/frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. 添加环境变量：
   - `VITE_API_URL` = `https://your-backend-server.com/api`
6. 点击 **Deploy**

### 7.3 Vercel 配置文件（可选）

在 `paper-translate/frontend` 创建 `vercel.json`：

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

---

## 8. 云服务器部署（生产推荐）

推荐配置：**Ubuntu 22.04 LTS + Docker + Nginx**，前端部署在 Netlify/Vercel，后端部署在云服务器。

### 8.1 服务器初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER
# 重新登录使生效

# 安装 Nginx
sudo apt install nginx -y

# 安装 Certbot（SSL 证书）
sudo apt install certbot python3-certbot-nginx -y
```

### 8.2 部署后端

```bash
# 克隆代码
git clone https://github.com/your-username/EasyTranslate.git
cd EasyTranslate/paper-translate

# 只启动后端（前端已部署到 Netlify/Vercel）
docker-compose up -d backend
```

### 8.3 配置 Nginx 反向代理

```bash
sudo nano /etc/nginx/sites-available/easytranslate
```

写入以下内容：

```nginx
server {
    listen 80;
    server_name api.your-domain.com;

    # 上传大小限制
    client_max_body_size 50M;

    # 代理到后端
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 长连接（WebSocket / 长轮询）
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/easytranslate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8.4 配置 SSL 证书

```bash
sudo certbot --nginx -d api.your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

### 8.5 配置 CORS

后端已默认允许所有来源（`allow_origins=["*"]`）。生产环境建议限定前端域名，修改 `backend/app/main.py`：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.netlify.app",
        "https://your-frontend.vercel.app",
        "https://www.your-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.6 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS
sudo ufw enable
```

### 8.7 生产推荐架构

```
用户浏览器
    │
    ▼
Netlify / Vercel（前端静态托管）
    │
    ▼ (API 请求)
Nginx（反向代理 + SSL）
    │
    ▼
Docker 容器（FastAPI 后端）
    │
    ▼
翻译 API（DeepL / OpenAI / Google）
```

---

## 9. 常见问题

### Q1: `npm install` 报错 `ETARGET` / `EJSONPARSE`

**原因**：某些依赖包版本不可用或 package.json 格式损坏。

**解决**：
```bash
# 删除依赖和锁文件
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

如果仍有问题，检查 `package.json` 是否为合法 JSON（[JSONLint](https://jsonlint.com/) 验证）。

### Q2: Docker `failed to connect to the docker daemon`

**原因**：Docker Desktop 没有启动。

**解决**：启动 Docker Desktop，等待托盘图标稳定后再执行命令。

### Q3: 前端 `Network Error`

**原因**：后端未启动或 API 地址不匹配。

**解决**：
1. 确认后端在 `http://localhost:8000` 运行（访问 `/health` 验证）
2. 本地开发：Vite proxy 自动转发 `/api` 到后端
3. 生产部署：确保 `VITE_API_URL` 环境变量正确指向后端地址

### Q4: 文件上传失败

**原因**：文件过大或格式不对。

**解决**：
- 确保文件为 PDF 格式
- 文件不超过 50MB
- 页数不超过 100 页
- Nginx 配置 `client_max_body_size 50M;`

### Q5: 翻译服务不工作

**原因**：翻译 API Key 未配置或网络不通。

**解决**：
1. 在前端翻译设置页面填入有效的 API Key
2. 确认服务器可以访问翻译 API（DeepL / OpenAI / Google）
3. 查看后端日志：`docker-compose logs -f backend`

### Q6: Docker 端口 80 被占用（Windows）

**原因**：IIS 或其他服务占用了 80 端口。

**解决**：修改 `docker-compose.yml` 端口映射：
```yaml
ports:
  - "3000:80"  # 改用其他端口
```

### Q7: 如何查看后端 API 文档？

后端集成了 Swagger UI，启动后访问：
- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

---

## 附录：翻译 API Key 获取

| 翻译引擎 | 获取地址 | 推荐度 |
|---------|---------|--------|
| DeepL Pro | https://www.deepl.com/pro-api | 翻译质量最佳 |
| OpenAI (GPT-4) | https://platform.openai.com/api-keys | 灵活度高 |
| Google Cloud | https://cloud.google.com/translate | 多语言覆盖广 |

---

**版本**：v1.0
**最后更新**：2026-04-24
