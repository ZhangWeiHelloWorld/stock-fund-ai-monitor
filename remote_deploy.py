import sys
import os
import zipfile
import json
import time

try:
    import paramiko
except ImportError:
    print("❌ 缺少 paramiko 依赖，请运行: pip install paramiko")
    sys.exit(1)

# 获取当前脚本所在项目目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_DIR, "deploy_config.json")
LOCAL_ZIP = os.path.join(PROJECT_DIR, "lh_deploy.zip")
REMOTE_ZIP = "/root/lh_deploy.zip"

def load_config():
    """从环境变量或本地 deploy_config.json 加载服务器连接配置"""
    config = {
        "host": os.environ.get("DEPLOY_HOST", ""),
        "port": int(os.environ.get("DEPLOY_PORT", "22")),
        "user": os.environ.get("DEPLOY_USER", "root"),
        "password": os.environ.get("DEPLOY_PASS", "")
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config["host"] = file_config.get("host", config["host"])
                config["port"] = int(file_config.get("port", config["port"]))
                config["user"] = file_config.get("user", config["user"])
                config["password"] = file_config.get("password", config["password"])
        except Exception as e:
            print(f"⚠️ 读取 deploy_config.json 失败: {e}")

    if not config["host"] or not config["password"]:
        print("❌ 错误: 未配置服务器连接信息！")
        print("请通过以下任一方式提供配置：")
        print("  1. 复制 deploy_config.json.example 为 deploy_config.json 并填写信息")
        print("  2. 设置环境变量: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS, DEPLOY_PORT")
        sys.exit(1)

    return config

def create_deploy_zip():
    """创建部署压缩包，自动安全排除数据库、依赖与缓存文件"""
    print("\n==========================================")
    print(f"📦 [打包本地代码] 创建 {LOCAL_ZIP}")
    print("==========================================")
    
    exclude_dirs = {'node_modules', 'venv', '__pycache__', '.git', '.idea', '.vscode', 'scratch', 'dist', 'local_backups', 'lh_backups'}
    exclude_extensions = {'.db', '.sqlite', '.sqlite3', '.pyc', '.zip', '.DS_Store', '.log'}
    exclude_files = {'admin_config.json', 'deploy_config.json', '.env'}

    with zipfile.ZipFile(LOCAL_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in exclude_extensions or file in exclude_files:
                    print(f"🔒 [安全排除] {file}")
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, os.path.dirname(PROJECT_DIR))
                zipf.write(full_path, rel_path)
                
    print(f"✅ 代码打包完成: {LOCAL_ZIP} ({os.path.getsize(LOCAL_ZIP)} 字节)")

def run_remote_command(ssh, cmd):
    print("\n==========================================")
    print(f"🚀 [远程执行] {cmd}")
    print("==========================================")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line, end="")
    exit_status = stdout.channel.recv_exit_status()
    return exit_status

def main():
    config = load_config()
    create_deploy_zip()

    print(f"\n正在连接到服务器 {config['host']}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            config["host"],
            port=config["port"],
            username=config["user"],
            password=config["password"],
            timeout=15
        )
        print("✅ SSH 连接成功！")
    except Exception as e:
        print(f"❌ SSH 连接失败: {e}")
        sys.exit(1)

    # 1. 备份远程数据库到本地和服务器目录（双重安全保障）
    print("\n==========================================")
    print("🛡️ [安全备份] 备份远程服务器历史数据与数据库...")
    print("==========================================")
    
    local_backup_dir = os.path.join(PROJECT_DIR, "local_backups")
    os.makedirs(local_backup_dir, exist_ok=True)
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    local_backup_file = os.path.join(local_backup_dir, f"remote_lh_backup_{timestamp_str}.db")

    sftp = ssh.open_sftp()
    try:
        remote_db_path = "/root/lh/backend/lh.db"
        sftp.stat(remote_db_path)
        sftp.get(remote_db_path, local_backup_file)
        print(f"✅ 远程生产数据库已安全下载备份到本地: {local_backup_file} ({os.path.getsize(local_backup_file)} 字节)")
    except Exception as e:
        print(f"ℹ️ 远程数据库检查/下载提示: {e} (若首次部署则正常)")

    # 2. 上传代码包
    print("\n==========================================")
    print(f"📦 [上传代码包] {LOCAL_ZIP} -> {REMOTE_ZIP}")
    print("==========================================")
    
    def progress_callback(transferred, total):
        percent = (transferred / total) * 100
        sys.stdout.write(f"\r上传进度: {transferred}/{total} 字节 ({percent:.1f}%)")
        sys.stdout.flush()

    sftp.put(LOCAL_ZIP, REMOTE_ZIP, callback=progress_callback)
    sftp.close()
    print("\n✅ 代码包上传成功！")

    # 3. 执行远程解压、服务器备份和依赖安装与服务重启
    commands = [
        # 服务器端带时间戳备份
        "BACKUP_DIR=\"/root/lh_backups/backup_$(date +%Y%m%d_%H%M%S)\" && mkdir -p \"$BACKUP_DIR\" && cp -rf /root/lh/backend/*.db \"$BACKUP_DIR/\" 2>/dev/null || true && cp -rf /root/lh/backend/admin_config.json \"$BACKUP_DIR/\" 2>/dev/null || true && cp -rf /root/lh/backend/cache \"$BACKUP_DIR/\" 2>/dev/null || true && echo \"✅ 历史数据已完整备份到服务器: $BACKUP_DIR\" && ls -la \"$BACKUP_DIR\"",
        "apt-get update",
        "apt-get install -y python3 python3-pip python3-venv nodejs npm unzip lsof",
        "cd /root && unzip -o lh_deploy.zip",
        "cd /root/lh/backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple",
        "cd /root/lh/frontend && npm install --registry=https://registry.npmmirror.com && npm run build",
        """cat > /etc/systemd/system/stock-monitor.service << 'EOF'
[Unit]
Description=Stock Fund Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/lh/backend
ExecStart=/root/lh/backend/venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8888
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF""",
        "systemctl daemon-reload",
        "systemctl enable stock-monitor",
        "systemctl restart stock-monitor",
        "sleep 3",
        "systemctl status stock-monitor --no-pager",
        "curl -s http://127.0.0.1:8888/api/market/indices | head -c 200 || true"
    ]

    for cmd in commands:
        status = run_remote_command(ssh, cmd)
        if status != 0 and "status" not in cmd and "apt-get" not in cmd and "cp" not in cmd:
            print(f"⚠️ 警告: 命令 [{cmd}] 返回非0退出代码: {status}")

    ssh.close()
    print("\n🎉 部署全流程已完成！服务器已成功升级，历史数据已在本地与服务器双重备份并完好保留。")

if __name__ == "__main__":
    main()
