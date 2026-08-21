# 📈 Stock & Fund AI Monitor (股票与基金实时监控与 AI 智能预警推送系统)

一款轻量级、全功能、开箱即用的 **A 股股票与公募基金实时行情监控、多维度异动预警、多用户持仓管理及 DeepSeek AI 智能复盘推送平台**。

支持 **x86_64 (amd64)** 与 **ARM64 (arm64/Apple Silicon/树莓派/ARM云服务器)** 跨平台原生多架构。

---

## 🚀 快速开始 (Quick Start)

### 1. 基础单行运行命令 (一秒启动)

```bash
docker run -d \
  --name stock-fund-monitor \
  -p 8888:8888 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  dazhangwei/stock-fund-ai-monitor:latest
```

启动完成后，在浏览器中访问：`http://localhost:8888` 即可进入管理系统。
- **默认管理员账号**：`admin`
- **默认管理员密码**：`admin123456`

---

### 2. 自定义参数运行 (带环境变量配置)

```bash
docker run -d \
  --name stock-fund-monitor \
  -p 9000:9000 \
  -v /opt/stock-monitor/data:/app/data \
  -e PORT=9000 \
  -e TZ=Asia/Shanghai \
  -e ADMIN_USERNAME=myadmin \
  -e ADMIN_PASSWORD=StrongPassword123 \
  --restart unless-stopped \
  dazhangwei/stock-fund-ai-monitor:latest
```

---

### 3. 使用 Docker Compose 部署 (推荐)

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  stock-fund-monitor:
    image: dazhangwei/stock-fund-ai-monitor:latest
    container_name: stock-fund-monitor
    restart: unless-stopped
    ports:
      - "8888:8888"
    environment:
      - TZ=Asia/Shanghai
      - PORT=8888
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=admin123456
    volumes:
      - ./data:/app/data
```

启动服务：
```bash
docker compose up -d
```

查看运行日志：
```bash
docker compose logs -f
```

停止服务：
```bash
docker compose down
```

---

## ⚙️ 环境变量与参数列表

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PORT` | `8888` | 服务监听的 HTTP 端口 |
| `HOST` | `0.0.0.0` | 服务监听的主机地址 |
| `TZ` | `Asia/Shanghai` | 容器时区（务必保持为北京时间，确保 A 股交易时段及定时推送精准生效） |
| `DATA_DIR` | `/app/data` | 数据持久化目录（存储 SQLite 数据库 `lh.db` 及配置） |
| `DB_PATH` | `/app/data/lh.db` | SQLite 数据库文件绝对路径 |
| `ADMIN_CONFIG_PATH` | `/app/data/admin_config.json` | 管理员配置文件存储路径 |
| `ADMIN_USERNAME` | `admin` | 首次初始化创建的管理员登录用户名 |
| `ADMIN_PASSWORD` | `admin123456` | 首次初始化创建的管理员登录密码 |

---

## 💾 数据持久化说明

容器内所有用户持仓数据、行情监控记录、系统设置以及管理员账户信息均持久化存储在 `/app/data` 目录下的 SQLite 数据库中。

**必须挂载宿主机目录**：
```bash
-v /宿主机本地路径:/app/data
```
挂载后，容器重启、销毁或升级新版本镜像，您的持仓数据和系统配置均不会丢失。

---

## 🔗 相关链接

- **GitHub 源码仓库**: [https://github.com/ZhangWeiHelloWorld/stock-fund-ai-monitor](https://github.com/ZhangWeiHelloWorld/stock-fund-ai-monitor)
- **Docker Hub 镜像**: [https://hub.docker.com/r/dazhangwei/stock-fund-ai-monitor](https://hub.docker.com/r/dazhangwei/stock-fund-ai-monitor)
