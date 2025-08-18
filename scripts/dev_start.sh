#!/bin/bash

# 本地开发环境一键启动脚本
set -e

echo "🚀 启动 Gitee-Notion 同步服务开发环境..."

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

echo "📋 检查 Python 版本..."
python3 --version

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

echo "🔧 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -q -r requirements.txt

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚙️  创建 .env 文件..."
    cat > .env << EOF
# 基础配置
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# 数据库配置
DB_URL=sqlite:///data/sync.db

# Gitee 配置
GITEE_WEBHOOK_SECRET=dev-secret

# Notion 配置 (可选)
# NOTION_TOKEN=your-notion-token
# NOTION_DATABASE_ID=your-database-id

# 可选功能
RATE_LIMIT_PER_MINUTE=60
MAX_REQUEST_SIZE=2097152
DEADLETTER_REPLAY_TOKEN=dev-replay-token

# 测试配置
RUN_INTEGRATION_TESTS=0
RUN_PERF_TESTS=0
RUN_RATE_LIMIT_TESTS=0
EOF
    echo "📝 已创建 .env 文件，请根据需要修改配置"
fi

# 确保数据目录存在
echo "📂 检查数据目录..."
mkdir -p data

# 初始化数据库
echo "🗄️  初始化数据库..."
python -c "from app.models import init_db; init_db()"

# 运行 Alembic 迁移
echo "🔄 运行数据库迁移..."
alembic stamp head

# 运行测试
echo "🧪 运行测试..."
python -m pytest tests/ -v --tb=short -x

echo "✅ 开发环境准备完成！"
echo ""
echo "📚 可用的启动命令："
echo "  开发服务器:     uvicorn app.server:app --reload --host 0.0.0.0 --port 8000"
echo "  生产服务器:     uvicorn app.server:app --host 0.0.0.0 --port 8000"
echo "  Docker 开发:    docker-compose up --build"
echo ""
echo "📊 可用的端点："
echo "  健康检查:       http://localhost:8000/health"
echo "  API 文档:       http://localhost:8000/docs"
echo "  Prometheus:     http://localhost:8000/metrics"
echo ""
echo "🔧 管理命令："
echo "  重放死信:       python scripts/replay_deadletter.py"
echo "  数据库迁移:     alembic revision --autogenerate -m 'description'"
echo "  升级数据库:     alembic upgrade head"
echo ""

# 询问是否启动开发服务器
read -p "🤔 是否立即启动开发服务器? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 启动开发服务器..."
    uvicorn app.server:app --reload --host 0.0.0.0 --port 8000
fi
