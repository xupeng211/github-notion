#!/bin/bash
set -euo pipefail

echo "🚀 手动部署 GitHub-Notion 同步系统到 AWS..."

# 配置变量
AWS_SERVER="3.35.106.116"
APP_DIR="/opt/github-notion-sync"
SERVICE_NAME="github-notion-sync"

# 检查 SSH 密钥
if [ ! -f ~/.ssh/aws-key.pem ]; then
    echo "❌ SSH 密钥不存在: ~/.ssh/aws-key.pem"
    echo "请将 AWS 私钥保存到 ~/.ssh/aws-key.pem 并设置权限 600"
    exit 1
fi

# 设置 SSH 密钥权限
chmod 600 ~/.ssh/aws-key.pem

echo "📤 传输文件到服务器..."

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "📁 临时目录: $TEMP_DIR"

# 复制应用文件
cp -r app/ $TEMP_DIR/
cp requirements.txt $TEMP_DIR/
cp -r alembic/ $TEMP_DIR/ 2>/dev/null || echo "⚠️  alembic 目录不存在，跳过"
cp alembic.ini $TEMP_DIR/ 2>/dev/null || echo "⚠️  alembic.ini 不存在，跳过"

# 创建部署脚本
cat > $TEMP_DIR/deploy_on_server.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "🚀 在服务器上执行部署..."

# 设置变量
APP_DIR="/opt/github-notion-sync"
SERVICE_NAME="github-notion-sync"

# 停止现有服务
echo "⏹️  停止现有服务..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || echo "服务未运行"
sudo pkill -f "uvicorn app.server:app" 2>/dev/null || echo "没有运行的进程"

# 创建应用目录
echo "📁 准备应用目录..."
sudo mkdir -p $APP_DIR
sudo chown ubuntu:ubuntu $APP_DIR
cd $APP_DIR

# 备份现有配置
if [ -f .env ]; then
    cp .env .env.backup
    echo "💾 已备份现有配置"
fi

# 清理旧文件
rm -rf app/ alembic/ *.py *.txt *.ini 2>/dev/null || true

echo "⏳ 等待文件传输完成..."
sleep 3

# 检查 Python 环境
echo "🐍 检查 Python 环境..."
python3 --version

# 升级 pip
echo "📦 升级 pip..."
python3 -m pip install --upgrade pip --user

# 安装依赖
echo "📦 安装依赖..."
python3 -m pip install --user \
    fastapi==0.111.0 \
    uvicorn[standard]==0.30.1 \
    pydantic==1.10.22 \
    email-validator==2.2.0 \
    starlette==0.37.2 \
    typing-extensions==4.14.1 \
    sqlalchemy==2.0.30 \
    httpx==0.27.0 \
    requests==2.31.0 \
    python-dotenv==1.0.1 \
    prometheus-client==0.20.0 \
    python-json-logger==2.0.7 \
    cryptography==42.0.5 \
    pyopenssl==24.0.0 \
    boto3==1.34.51 \
    apscheduler==3.10.4 \
    pyyaml==6.0.1 \
    alembic==1.13.2

# 创建环境配置（如果不存在）
if [ ! -f .env ]; then
    echo "⚙️  创建环境配置..."
    cat > .env << ENVEOF
ENVIRONMENT=production
DB_URL=sqlite:///./data/app.db
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=100
MAX_REQUEST_SIZE=2097152
DISABLE_NOTION=false
ENVEOF
    echo "⚠️  请手动设置以下环境变量:"
    echo "   GITHUB_WEBHOOK_SECRET"
    echo "   NOTION_TOKEN"
    echo "   NOTION_DATABASE_ID"
    echo "   GITHUB_TOKEN"
    echo "   DEADLETTER_REPLAY_TOKEN"
fi

# 创建数据目录
mkdir -p data logs

# 初始化数据库
echo "🗄️  初始化数据库..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.models import init_db
    init_db()
    print('✅ 数据库初始化完成')
except Exception as e:
    print(f'⚠️  数据库初始化失败: {e}')
    print('继续部署...')
"

# 创建 systemd 服务
echo "🔧 创建系统服务..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << SERVICEEOF
[Unit]
Description=GitHub-Notion Sync Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment=PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/.local/bin/uvicorn app.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

# 重新加载 systemd
echo "🔄 重新加载 systemd..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# 启动服务
echo "🚀 启动服务..."
sudo systemctl start $SERVICE_NAME

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
sudo systemctl status $SERVICE_NAME --no-pager

# 检查端口
echo "🔍 检查端口 8000..."
sudo netstat -tlnp | grep :8000 || echo "端口 8000 未监听"

# 测试健康检查
echo "🏥 测试健康检查..."
curl -f http://localhost:8000/health 2>/dev/null && echo "✅ 健康检查通过" || echo "❌ 健康检查失败"

echo "✅ 部署完成！"
echo "🌐 服务地址: http://3.35.106.116:8000"
echo "🏥 健康检查: http://3.35.106.116:8000/health"
echo "📊 监控指标: http://3.35.106.116:8000/metrics"
EOF

# 传输文件到服务器
echo "📤 传输应用文件..."
scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no -r $TEMP_DIR/* ubuntu@$AWS_SERVER:$APP_DIR/

# 传输并执行部署脚本
echo "🚀 执行远程部署..."
scp -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no $TEMP_DIR/deploy_on_server.sh ubuntu@$AWS_SERVER:/tmp/
ssh -i ~/.ssh/aws-key.pem -o StrictHostKeyChecking=no ubuntu@$AWS_SERVER "chmod +x /tmp/deploy_on_server.sh && /tmp/deploy_on_server.sh"

# 清理临时目录
rm -rf $TEMP_DIR

echo "🎉 手动部署完成！"
echo "🔍 验证部署..."

# 等待服务完全启动
sleep 15

# 验证部署
if curl -f http://$AWS_SERVER:8000/health >/dev/null 2>&1; then
    echo "✅ 部署验证成功！服务正常运行"
    echo "🌐 访问地址: http://$AWS_SERVER:8000"
else
    echo "❌ 部署验证失败，请检查服务状态"
    echo "🔍 可以通过以下命令检查:"
    echo "   ssh -i ~/.ssh/aws-key.pem ubuntu@$AWS_SERVER 'sudo systemctl status github-notion-sync'"
    echo "   ssh -i ~/.ssh/aws-key.pem ubuntu@$AWS_SERVER 'sudo journalctl -u github-notion-sync -f'"
fi
