---
name: docker-cicd-publisher
description: >-
  Automates the complete containerization and CI/CD publishing workflow for any GitHub repository.
  Creates multi-stage Dockerfile, .dockerignore, docker-compose.yml, fetches Docker Hub credentials
  from MCP, automatically injects GitHub Actions Secrets via API, and configures multi-architecture
  (AMD64 & ARM64) remote builds without building locally.
---

# Docker Multi-Arch CI/CD Publisher Skill

本 Skill 用于将任意 GitHub 仓库快速容器化，并通过 GitHub Actions 远程自动化打包多架构（`linux/amd64` 与 `linux/arm64`）Docker 镜像推送到 Docker Hub，无需在本地占用资源构建镜像。

---

## 🌟 适用场景与触发条件

- 用户要求：“将项目容器化并上传到 Docker Hub”
- 用户要求：“在 GitHub 上自动构建 AMD/ARM 镜像”
- 用户要求：“添加 Dockerfile 和 GitHub Actions workflow 流程”
- 项目缺少 Dockerfile 或缺少远程 CI/CD 构建发布流程时。

---

## 🛠️ 全流程执行步骤 (Standard Operating Procedure)

### 第一步：技术栈识别与代码参数适配 (Stack Analysis)

1. **识别项目架构**：
   - **前端**：检查是否存在 `frontend/`、`package.json`（Vue/React/Vite/Next/Nuxt 等），确定构建命令（`npm run build`）与产物输出目录（`dist/` 或 `build/`）。
   - **后端**：检查 Python（FastAPI/Flask/Django）、Node.js、Go、Java 等。
   - **数据与持久化**：确定数据库文件（如 SQLite `*.db`）、上传文件目录（`uploads/`、`data/`）。
2. **代码运行时参数改造**：
   - 确保后端从环境变量读取配置，提供合理默认值：
     - `PORT`：服务端口（如 `os.environ.get("PORT", 8888)`）
     - `HOST`：监听地址（默认 `0.0.0.0`）
     - `DATA_DIR` / `DB_PATH`：持久化存储目录（支持容器挂载）
     - `TZ`：时区配置（如国内股票/行情系统必须为 `Asia/Shanghai`）
     - 初始管理员账号密码等

---

### 第二步：生成标准容器化文件 (Docker Files Generation)

#### 1. `Dockerfile`（多阶段构建规范）
- **Stage 1 (Frontend Builder)**：使用轻量镜像（如 `node:20-alpine`）独立编译前端。
- **Stage 2 (Runtime)**：使用官方精简运行时（如 `python:3.11-slim`、`alpine` 等）。
- **时区与证书**：安装 `tzdata` 与 `ca-certificates`，设置 `ENV TZ=Asia/Shanghai`。
- **持久化卷**：声明 `VOLUME ["/app/data"]` 并预创建目录。
- **健康检查**：添加 `HEALTHCHECK` 探针。
- **启动命令**：使用参数化环境变量启动。

#### 2. `.dockerignore`
必须包含：
```dockerignore
.git
.github
node_modules
frontend/node_modules
dist
build
venv
__pycache__
*.pyc
*.db
*.log
scratch
deploy_config.json
.DS_Store
```

#### 3. `docker-compose.yml`
提供开箱即用的一键启动模版，包含 `restart: unless-stopped`、`ports`、`environment` 及 `volumes` 挂载。

---

### 第三步：MCP 凭据提取与 GitHub Secrets 自动注入

1. **从 MCP 配置提取凭据**：
   - 读取 `~/.gemini/config/mcp_config.json` 或环境变量：
     - Docker Hub: `HUB_USERNAME`、`HUB_PAT_TOKEN`
     - GitHub: `GITHUB_PERSONAL_ACCESS_TOKEN`
2. **通过 GitHub REST API 自动注入 Secrets**：
   - 获取仓库公钥：`GET https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key`
   - 使用 LibSodium (`nacl.public.SealedBox`) 加密：
     - `DOCKERHUB_USERNAME`
     - `DOCKERHUB_TOKEN`
   - 写入 Secrets：`PUT https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}`

---

### 第四步：配置 GitHub Actions 多架构构建工作流

在 `.github/workflows/docker-publish.yml` 中配置：
- **触发条件**：`push: branches: [main]`, `tags: ['v*.*.*']`, `workflow_dispatch`
- **QEMU 模拟器**：`docker/setup-qemu-action@v3`（支持 `linux/amd64,linux/arm64`）
- **Buildx 构建器**：`docker/setup-buildx-action@v3`
- **Docker Hub 登录**：`docker/login-action@v3`
- **元数据提取**：`docker/metadata-action@v5`
- **编译与推送**：`docker/build-push-action@v6`，启用 GHA 缓存加速（`cache-from: type=gha`, `cache-to: type=gha,mode=max`）。

---

### 第五步：完善部署文档与 Docker Hub 说明

1. 在 `README.md` 中增加：
   - 单行 `docker run` 命令
   - 挂载持久化存储说明 (`-v`)
   - 环境变量完整配置表
   - `docker-compose` 启动与管理命令
   - 多架构兼容说明（x86_64 & ARM64/Apple Silicon）
2. 生成 `DOCKER_HUB_README.md` 用于 Docker Hub 仓库主页展示。

---

### 第六步：代码推送与 CI/CD 远端监控

1. 将所有文件提交并 `git push` 到 GitHub 远程仓库。
2. 严格遵循**不在本地生成镜像**原则。
3. 轮询/监听 GitHub Actions 运行状态，确保构建与上传成功。

---

## 🛡️ 最佳实践与易漏项自检

1. **时区问题**：定时任务调度（如 APScheduler/Cron）极易受 UTC 默认时区影响，务必在 Dockerfile 中配置 `tzdata` 并设置 `TZ=Asia/Shanghai`。
2. **文件权限与目录创建**：挂载外部 Volume 时，后端代码初始化时必须使用 `os.makedirs(..., exist_ok=True)` 保证数据库与日志路径存在。
3. **前端静态资源捕获**：SPA 单页应用在 FastAPI / Express 中挂载时，需配置 fallback 路由（404 时指向 `index.html`），并避开 `/api/` 路由。
4. **多架构交叉编译耗时**：QEMU 模拟 arm64 构建速度稍慢（通常 2~4 分钟），务必配置 GitHub Actions Cache 加快二次构建速度。
