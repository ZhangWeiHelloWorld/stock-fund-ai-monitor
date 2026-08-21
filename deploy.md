# 部署文档 — 股票基金监控系统

## 服务器要求
- OS: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- Python 3.9+
- Node.js 18+（用于构建前端，之后可卸载）
- 端口 8888 开放

---

## 一、上传代码到服务器

### 方式 1：使用自动化部署脚本（推荐）
1. 复制配置文件模板：
   ```bash
   cp deploy_config.json.example deploy_config.json
   ```
2. 编辑 `deploy_config.json`，填入您的服务器 IP 和 SSH 密码。
3. 执行部署脚本：
   ```bash
   python3 remote_deploy.py
   ```

### 方式 2：手动打包上传
```bash
zip -r lh.zip backend frontend start.sh requirements.txt
scp lh.zip user@<YOUR_SERVER_IP>:/home/user/
ssh user@<YOUR_SERVER_IP>
unzip lh.zip -d lh
```

---

## 二、安装系统依赖

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm unzip

# CentOS / RHEL
sudo yum install -y python3 python3-pip nodejs npm unzip
```

---

## 三、一键启动（测试与前台运行）

```bash
cd /home/user/lh
chmod +x start.sh
./start.sh
```

访问 `http://<YOUR_SERVER_IP>:8888` 即可看到系统界面。

---

## 四、生产环境：systemd 守护进程

### 4.1 构建前端

```bash
cd /home/user/lh/frontend
npm install
npm run build
```

### 4.2 安装 Python 依赖

```bash
cd /home/user/lh/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 创建 systemd 服务

```bash
sudo nano /etc/systemd/system/stock-monitor.service
```

写入以下内容（根据实际部署路径调整 `WorkingDirectory` 和 `ExecStart`）：

```ini
[Unit]
Description=Stock Fund Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/user/lh/backend
ExecStart=/home/user/lh/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8888
Restart=always
RestartSec=5
Environment=PYTHONPATH=/home/user/lh/backend

[Install]
WantedBy=multi-user.target
```

```bash
# 重载并启动服务
sudo systemctl daemon-reload
sudo systemctl enable stock-monitor
sudo systemctl start stock-monitor

# 查看运行状态
sudo systemctl status stock-monitor

# 实时查看日志
sudo journalctl -u stock-monitor -f
```

---

## 五、防火墙与端口放行

```bash
# Ubuntu UFW
sudo ufw allow 8888/tcp
sudo ufw reload

# CentOS firewalld
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --reload
```

---

## 六、配置企业微信推送与回调

1. 打开浏览器访问 `http://<YOUR_SERVER_IP>:8888`
2. 使用管理员账号登录（默认账号：`admin`，默认密码：`admin123456`，请登录后及时修改）
3. 进入 **系统设置** 页面：
   - **CorpID**: 在企业微信管理后台 →「我的企业」→ 企业ID
   - **AgentID**: 企业微信自建应用的 AgentID
   - **Secret**: 企业微信自建应用的 Secret
   - **推送接收人**: 填写成员 UserID（多人用 `|` 分隔），或填 `@all` 发送给全员
4. 点击 **保存配置** 并点击 **测试推送** 验证。

### 企业微信管理后台接收消息服务器配置（可选）

如需启用双向交互验证，在企业微信管理后台「接收消息」中填写：
- **URL**: `http://<YOUR_SERVER_IP>:8888/swx/receive`
- **Token**: 在系统设置中生成的 Token（或自定义）
- **EncodingAESKey**: 在系统设置中生成的 43 位 AESKey

---

## 七、数据持久化与自动备份

数据库文件默认位于：`backend/lh.db`

建议配置定时任务定期备份数据库：

```bash
# 编辑定时任务
crontab -e

# 每天凌晨 2:00 自动备份
0 2 * * * cp /home/user/lh/backend/lh.db /home/user/backups/lh_$(date +\%Y\%m\%d).db
```

---

## 八、版本更新

```bash
# 拉取新代码或上传新包后
cd /home/user/lh/frontend
npm run build
sudo systemctl restart stock-monitor
```

---

## 九、常见问题排查

| 问题现象 | 排查与解决方案 |
|---------|-------------|
| 端口 8888 被占用 | 执行 `lsof -i :8888` 查找占用进程并 `kill -9 <PID>` |
| 推送失败 | 检查 CorpID、Secret、AgentID 是否填写准确，网络是否可连通微信接口 |
| 行情数据不更新 | 检查当前是否为交易日交易时段，确认服务器能否访问外部行情接口 |
| 前端页面 404 | 确保 `frontend/dist` 产物已正确生成，执行 `npm run build` |
| 忘记管理员密码 | 修改 `backend/admin_config.json` 中的密码，重启服务或调用接口即可重置 |
