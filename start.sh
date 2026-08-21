#!/bin/bash

# ===================================================
# 股票基金监控系统 - 启动脚本
# ===================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "======================================"
echo "  股票基金监控系统 启动中..."
echo "======================================"

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

# 检查 Node.js（用于构建前端）
if ! command -v node &>/dev/null; then
    echo "⚠️  未找到 node，跳过前端构建（如已有 dist 目录则继续）"
    BUILD_FRONTEND=false
else
    BUILD_FRONTEND=true
fi

# ---- 安装 Python 依赖 ----
echo ""
echo "📦 安装 Python 依赖..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
echo "✅ Python 依赖安装完成"

# ---- 构建前端 ----
if [ "$BUILD_FRONTEND" = true ]; then
    echo ""
    echo "🔨 构建前端..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    echo "✅ 前端构建完成"
else
    echo "⚠️  跳过前端构建"
fi

# ---- 启动后端 ----
echo ""
echo "🚀 启动后端服务 (端口 8888)..."
cd "$BACKEND_DIR"
source venv/bin/activate

echo "======================================"
echo "  本地访问地址: http://localhost:8888"
echo "  企业微信接收: http://<服务器IP或域名>:8888/swx/receive"
echo "======================================"

python3 -m uvicorn main:app --host 0.0.0.0 --port 8888 --reload
