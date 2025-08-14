#!/bin/bash
# 在 EC2 服务器上执行的完整配置脚本
# 目标：配置 Nginx 反向代理，确保 GitHub Webhook 返回 200

set -e

echo "🚀 开始在 EC2 服务器上配置 GitHub-Notion 同步系统..."
echo "服务器: $(hostname -I | awk '{print $1}')"
echo "时间: $(date)"
echo "======================================================="

# 1. 检查系统环境
echo "🔍 检查系统环境..."
echo "系统信息: $(lsb_release -d 2>/dev/null || echo "Ubuntu")"
echo "用户: $(whoami)"
echo "工作目录: $(pwd)"

# 2. 检查必需的文件
echo "📁 检查部署文件..."
required_files=("nginx-app.conf" "infrastructure-only.sh" "verify.sh")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 错误: 找不到文件 $file"
        exit 1
    fi
done
echo "✅ 所有部署文件检查完成"

# 3. 检查 Nginx 是否安装
echo "🔍 检查 Nginx 安装状态..."
if ! command -v nginx >/dev/null 2>&1; then
    echo "📦 安装 Nginx..."
    sudo apt update
    sudo apt install -y nginx
    echo "✅ Nginx 安装完成"
else
    echo "✅ Nginx 已安装"
fi

# 4. 检查 Nginx 状态
echo "🔄 检查并启动 Nginx..."
if ! systemctl is-active --quiet nginx; then
    sudo systemctl start nginx
fi
sudo systemctl enable nginx
echo "✅ Nginx 服务已启动并设置为开机自启"

# 5. 创建项目目录
echo "📁 创建项目目录..."
PROJECT_DIR="/opt/gitee-notion-sync"
if [ ! -d "$PROJECT_DIR" ]; then
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown ubuntu:ubuntu "$PROJECT_DIR"
    echo "✅ 项目目录创建完成: $PROJECT_DIR"
else
    echo "✅ 项目目录已存在: $PROJECT_DIR"
fi

# 6. 创建数据目录（为 CI/CD 容器挂载做准备）
echo "📁 创建数据目录..."
sudo mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/logs"
sudo chown ubuntu:ubuntu "$PROJECT_DIR/data" "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/data" "$PROJECT_DIR/logs"
echo "✅ 数据目录创建完成"

# 7. 创建 Nginx 日志目录
echo "📁 创建 Nginx 日志目录..."
sudo mkdir -p /var/log/nginx
echo "✅ Nginx 日志目录准备完成"

# 8. 备份现有 Nginx 配置
echo "💾 备份现有 Nginx 配置..."
if [ -f "/etc/nginx/sites-available/app.conf" ]; then
    sudo cp /etc/nginx/sites-available/app.conf "/etc/nginx/sites-available/app.conf.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 现有配置已备份"
fi

# 9. 部署 Nginx 配置
echo "⚙️ 部署 Nginx 反向代理配置..."
sudo cp nginx-app.conf /etc/nginx/sites-available/app.conf
echo "✅ Nginx 配置文件部署完成"

# 10. 启用站点配置
echo "🔗 启用站点配置..."
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ 站点配置已启用，默认站点已禁用"

# 11. 测试 Nginx 配置
echo "🧪 测试 Nginx 配置..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置语法正确"
else
    echo "❌ Nginx 配置语法错误"
    exit 1
fi

# 12. 重新加载 Nginx
echo "🔄 重新加载 Nginx..."
sudo systemctl reload nginx
echo "✅ Nginx 已重新加载"

# 13. 检查服务状态
echo "📊 检查服务状态..."
echo "Nginx 状态:"
sudo systemctl status nginx --no-pager | head -8
echo ""
echo "端口监听情况:"
sudo ss -tlnp | grep -E ':(80|8000)' || echo "当前端口监听: $(sudo ss -tlnp | grep -E ':80' | head -2)"

# 14. 检查防火墙设置
echo "🔥 检查防火墙设置..."
if command -v ufw >/dev/null 2>&1; then
    sudo ufw status | head -5
    # 确保端口开放
    sudo ufw allow 80/tcp >/dev/null 2>&1 || true
    sudo ufw allow 8000/tcp >/dev/null 2>&1 || true
    echo "✅ 防火墙端口已开放"
else
    echo "✅ 未检测到 ufw 防火墙"
fi

echo ""
echo "🎉 服务器基础设施配置完成！"
echo "======================================================="
echo "📋 配置总结:"
echo "  ✅ Nginx 反向代理: 80端口 → 8000端口"
echo "  ✅ 项目目录: $PROJECT_DIR"
echo "  ✅ 数据目录: $PROJECT_DIR/data"
echo "  ✅ 日志目录: $PROJECT_DIR/logs"
echo "  ✅ 配置文件: /etc/nginx/sites-available/app.conf"
echo ""
echo "📋 测试命令:"
echo "  curl -i http://localhost/health"
echo "  curl -i http://3.35.106.116/health"
echo ""
echo "📋 下一步:"
echo "  1. 推送代码到 GitHub 触发 CI/CD 部署"
echo "  2. CI/CD 会自动部署应用到 8000 端口"
echo "  3. GitHub Webhook 将通过 80端口 → 8000端口 访问成功"
echo ""
echo "🚀 现在你的服务器已准备好接收 CI/CD 部署了！" 