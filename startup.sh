#!/bin/bash
# 新城小米虾 启动脚本

cd "$(dirname "$0")"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装"
    exit 1
fi

# 检查依赖
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 创建必要目录
mkdir -p data
mkdir -p data/proofread_uploads
mkdir -p data/proofread_history

# 停止旧进程
lsof -ti:5001 | xargs kill -9 2>/dev/null

echo "╔══════════════════════════════════════════╗"
echo "║     新城小米虾 + 密信本 集成系统            ║"
echo "║     http://localhost:5001                 ║"
echo "╚══════════════════════════════════════════╝"

# 启动
python3 app.py
