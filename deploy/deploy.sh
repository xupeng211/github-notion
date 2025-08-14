#!/bin/bash
# GitHub-Notion 双向同步系统部署脚本
# 作者: 后端与发布工程师
# 目标: 确保 GitHub Webhook 返回 200 状态码

set -e  # 遇到错误立即退出

echo "🚀 开始部署 GitHub-Notion 双向同步系统..."
echo "======================================================="

# 1. 确保在项目根目录
echo "📁 检查项目目录..."
if [ ! -f "app/server.py" ]; then
    echo "❌ 错误: 请在项目根目录执行此脚本"
    exit 1
fi
echo "✅ 项目目录确认"

# 2. 创建必需的目录
echo "📁 创建必需目录..."
sudo mkdir -p /var/log/nginx
mkdir -p data
mkdir -p logs
chmod 755 data logs
echo "✅ 目录创建完成: $(pwd)/data $(pwd)/logs"

# 3. 备份现有 Nginx 配置
echo "💾 备份现有配置..."
if [ -f "/etc/nginx/sites-available/app.conf" ]; then
    sudo cp /etc/nginx/sites-available/app.conf /etc/nginx/sites-available/app.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ 已备份现有配置"
fi

# 4. 部署 Nginx 配置
echo "⚙️ 部署 Nginx 配置..."
sudo cp deploy/nginx-app.conf /etc/nginx/sites-available/app.conf
echo "✅ Nginx 配置文件已复制到 /etc/nginx/sites-available/app.conf"

# 5. 启用站点配置
echo "🔗 启用站点配置..."
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf
echo "✅ 站点配置已启用"

# 6. 禁用默认站点（避免冲突）
echo "🚫 禁用默认站点..."
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ 默认站点已禁用"

# 7. 测试 Nginx 配置
echo "🧪 测试 Nginx 配置..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置测试通过"
else
    echo "❌ Nginx 配置测试失败"
    exit 1
fi

# 8. 重新加载 Nginx
echo "🔄 重新加载 Nginx..."
sudo systemctl reload nginx
echo "✅ Nginx 已重新加载"

# 9. 检查 Nginx 状态
echo "📊 检查 Nginx 状态..."
sudo systemctl status nginx --no-pager | head -10
echo "✅ Nginx 状态检查完成"

# 10. 检查端口监听
echo "🔍 检查端口监听..."
echo "端口 80 监听情况:"
sudo ss -tlnp | grep :80 || echo "  未找到端口 80 监听"
echo "端口 8000 监听情况:"
sudo ss -tlnp | grep :8000 || echo "  未找到端口 8000 监听"

echo ""
echo "🎉 Nginx 部署完成！"
echo "======================================================="
echo "📋 后续步骤:"
echo "  1. 确保 FastAPI 应用在 8000 端口运行"
echo "  2. 运行验证脚本: bash deploy/verify.sh"
echo "  3. 在 GitHub 中测试 Webhook"
echo "" 