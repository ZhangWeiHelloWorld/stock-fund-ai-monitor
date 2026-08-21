# 📈 Stock & Fund AI Monitor (股票与基金实时监控与 AI 智能预警推送系统)

<p align="center">
  <img src="https://img.shields.io/badge/Docker-Multi--Arch-2496ED?style=flat-square&logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/Vue-3.x-4FC08D?style=flat-square&logo=vue.js" alt="Vue 3" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/DeepSeek-AI%20Enabled-4A90E2?style=flat-square" alt="DeepSeek" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License" />
</p>

一款轻量级、全功能、开箱即用的 **A 股股票与公募基金实时行情监控、多维度异动预警、多用户持仓管理及 DeepSeek AI 智能复盘推送平台**。

---

## 🌟 核心功能特性

### 1. 📊 持仓与收益全景监控
- **股票实时行情**：实时追踪持仓与自选 A 股股票价格、涨跌幅、持仓成本、当日盈亏、累计盈亏及持仓占比。
- **基金盘中实时估值**：接入天天基金与新浪基金接口，实时跟踪场外基金盘中估值、单位净值及估算盈亏。
- **历史收益与资产曲线**：按交易日自动归档与计算历史盈亏走势，清晰直观掌握资产变动趋势。

### 2. ⚡ 多维度异动波动预警
- **涨跌幅阈值预警**：股票/基金达到自定义涨跌幅阈值（如涨幅 ≥ +5%、跌幅 ≤ -5%）即时触发推送。
- **日内极值触及提醒**：支持监测股价触及或突破日内最高价/跌破日内最低价提醒。
- **短时间剧烈振幅监控**：支持设定统计窗口（如 5 分钟内）与异动幅度（如 ≥ 3%），敏锐捕捉盘中火箭拉升或跳水行情。
- **智能防刷屏冷却**：内置防抖冷却时间机制（默认 15 分钟），避免短时间内对同一标的重复轰炸。

### 3. 🤖 DeepSeek / AI 大模型智能复盘与研报
- **交易日自动复盘**：每个交易日午盘（11:35）与收盘（15:05）自动汇总体量、持仓盈亏与宏观行情，由 DeepSeek 大模型生成全方位复盘报告（持仓点评、宏观政治局势分析、板块热点轮动、短中期展望、操作与风控建议）。
- **通用 OpenAI 兼容**：支持 DeepSeek 官方 API 及任意 OpenAI 兼容大模型（如 ChatGPT、Claude、Qwen 等）。

### 4. 📰 AI 实时财经新闻持仓影响分析
- **全网快讯智能抓取**：自动从各大主流财经媒体抓取最新宏观与个股快讯。
- **持仓针对性解读**：AI 结合当前用户实际持仓进行利好/利空深度研判（评级：🟢 显著利好 / 🔴 显著利空 / 🟡 中性观望），并提供短中线应对策略。

### 5. 🔔 企业微信全场景即时推送
- **应用消息推送**：深度打通企业微信自建应用，支持图文排版、Markdown 及格式化卡片推送。
- **丰富推送场景**：支持开盘（09:30）速递、盘中定时快报（支持自定义间隔）、收盘盘点、突发异动预警及 AI 深度研报。
- **双向交互**：支持企业微信接收消息服务器回调验证。

### 6. 👥 多用户独立隔离与管理
- **多用户持仓隔离**：支持多用户独立登录，各自管理独立的股票/基金持仓、推送设置及预警规则。
- **管理员权限体系**：管理员可分配新账号、重置密码及管理权限。
- **防遗忘密码重置**：支持通过后端配置文件安全找回管理员账号密码。

### 7. 🎨 现代极简毛玻璃 UI
- 采用现代 Glassmorphism 毛玻璃设计风格，支持 PC 端与手机移动端自适应浏览。

---

## 🏗️ 系统架构

```text
┌─────────────────────────────────────────────────────────────┐
│                      用户终端 (PC / 手机)                    │
└──────────────┬───────────────────────────────┬──────────────┘
               │ HTTP / JSON                   │ WeCom 推送
               ▼                               ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│     前端 (Vue 3 + Vite)      │ │   企业微信 (WeCom App API)    │
└──────────────┬───────────────┘ └─────────────▲───────────────┘
               │ RESTful API                   │ 消息推送
               ▼                               │
┌──────────────────────────────────────────────┴──────────────┐
│                    后端 (FastAPI / Python)                  │
│  ├─ 身份认证与权限 (JWT / PBKDF2 Auth)                      │
│  ├─ 行情与估值引擎 (新浪财经 / 天天基金)                     │
│  ├─ 波动预警与分析引擎 (Alert Engine)                       │
│  ├─ 定时调度器 (APScheduler)                               │
│  ├─ AI 分析服务 (DeepSeek / OpenAI Compatible)              │
│  └─ 本地持久化存储 (SQLite3 / lh.db)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速上手

### 环境要求
- **Python**: 3.9 或更高版本
- **Node.js**: 18.0 或更高版本
- **包管理器**: npm 或 pnpm / yarn

---

### 本地开发与运行

#### 1. 克隆代码库
```bash
git clone https://github.com/ZhangWeiHelloWorld/stock-fund-ai-monitor.git
cd stock-fund-ai-monitor
```

#### 2. 启动后端
```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # Windows 用户执行: venv\Scripts\activate
pip install -r requirements.txt

# 启动 FastAPI 服务 (默认端口 8888)
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

#### 3. 启动前端
在另一个终端窗口中：
```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`（开发模式）或 `http://localhost:8888`（集成构建后）即可访问。

---

### 一键脚本启动（本地）

```bash
chmod +x start.sh
./start.sh
```

---

## ⚙️ 系统配置指南

系统启动后，访问 `http://localhost:8888`，进入 **系统设置** 页面进行参数配置：

### 1. 初始登录凭证
- **默认管理员账号**：`admin`
- **默认管理员密码**：`admin123456`
> 💡 首次登录后，请务必在设置界面修改初始密码。

### 2. 企业微信配置
| 配置项 | 说明 | 示例 |
|--------|------|------|
| **CorpID** | 企业微信管理后台「我的企业」中的企业 ID | `wwxxxxxxxxxxxx` |
| **AgentID** | 自建应用的 AgentId | `1000002` |
| **Secret** | 自建应用的 AppSecret | `xxxxxxxxxxxxxxxx` |
| **推送接收人** | 成员 UserID，多人用 `\|` 分隔，或填 `@all` | `@all` 或 `user1\|user2` |

### 3. AI 大模型配置
| 配置项 | 说明 | 示例 |
|--------|------|------|
| **API Key** | DeepSeek 或 OpenAI 兼容平台的 API 密钥 | `sk-xxxxxxxx` |
| **Base URL** | 接口服务地址 | `https://api.deepseek.com` |
| **Model** | 调用的模型名称 | `deepseek-chat` |

---

## 🚢 生产环境部署

### 方式一：Docker 容器化部署（推荐）

本项目已发布原生支持 **x86_64 (amd64)** 与 **ARM64 (arm64)** 架构的多架构官方镜像，开箱即用。

#### 1. 快速单行启动
```bash
docker run -d \
  --name stock-fund-monitor \
  -p 8888:8888 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  dazhangwei/stock-fund-ai-monitor:latest
```

#### 2. 自定义参数启动
```bash
docker run -d \
  --name stock-fund-monitor \
  -p 9000:9000 \
  -v /opt/stock-monitor/data:/app/data \
  -e PORT=9000 \
  -e TZ=Asia/Shanghai \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=your_password \
  --restart unless-stopped \
  dazhangwei/stock-fund-ai-monitor:latest
```

#### 3. 使用 Docker Compose 一键启动
在项目根目录下或任意目录创建 `docker-compose.yml`：
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

启动与管理：
```bash
docker compose up -d       # 后台启动
docker compose logs -f     # 查看运行日志
docker compose down        # 停止服务
```

#### 4. Docker 运行时环境变量配置表

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PORT` | `8888` | 服务监听的 HTTP 端口 |
| `HOST` | `0.0.0.0` | 服务监听的主机地址 |
| `TZ` | `Asia/Shanghai` | 容器时区（保证 A 股交易时间与推送调度精准） |
| `DATA_DIR` | `/app/data` | 数据持久化目录（存储 SQLite `lh.db` 及配置） |
| `DB_PATH` | `/app/data/lh.db` | SQLite 数据库文件绝对路径 |
| `ADMIN_CONFIG_PATH` | `/app/data/admin_config.json` | 管理员配置文件存储路径 |
| `ADMIN_USERNAME` | `admin` | 首次初始化创建的管理员登录用户名 |
| `ADMIN_PASSWORD` | `admin123456` | 首次初始化创建的管理员登录密码 |

---

### 方式二：一键远程自动化部署脚本
1. 复制部署配置文件模板：
   ```bash
   cp deploy_config.json.example deploy_config.json
   ```
2. 编辑 `deploy_config.json` 填入您的服务器 IP 和 SSH 凭证：
   ```json
   {
     "host": "your_server_ip",
     "port": 22,
     "user": "root",
     "password": "your_server_ssh_password"
   }
   ```
3. 在本地运行部署脚本：
   ```bash
   python3 remote_deploy.py
   ```

### 方式三：Systemd 生产守护进程
参考完整的 [部署指南 (deploy.md)](deploy.md) 进行配置。

---

## 🛡️ 安全与数据隔离

- 🔐 **本地数据隔离**：本地 SQLite 数据库文件（`backend/*.db`）及密码配置文件默认被 `.gitignore` 保护，不会被提交或泄露。
- 🔑 **密码哈希存储**：用户密码采用带 Salt 随机盐的 `PBKDF2-HMAC-SHA256` 算法哈希存储。
- 🛡️ **无硬编码机密**：所有服务器连接凭据与 API Key 均支持环境变量或本地未跟踪配置文件加载。

---

## 📅 后续开发计划 (Roadmap)

- [ ] **多通知渠道拓展**：增加钉钉机器人、飞书 Webhook、Telegram Bot 与邮件推送。
- [ ] **K线图表与技术指标预警**：集成 Lightweight Charts / ECharts，支持 MACD / KDJ / 均线金叉死叉预警。
- [ ] **行业板块与热点图谱**：A 股行业板块涨跌排行、资金净流入流出热力图。
- [ ] **智能网格与模拟回测**：支持预设网格挂单策略模拟与收益回测分析。
- [x] **容器化支持**：提供 Dockerfile 与 `docker-compose.yml` 一键编排及多架构自动构建方案。

---

## 📄 开源许可证 (License)

本项目采用 [MIT License](LICENSE) 开源授权。
