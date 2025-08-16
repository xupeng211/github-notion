#!/bin/bash
# 基础设施配置脚本 - 适配 CI/CD 环境
# 目标：只配置 Nginx 反向代理，不管理应用部署

set -e

echo "🏗️ 配置基础设施以支持 CI/CD 部署的应用..."
echo "======================================================="

# 1. 检查项目目录结构
echo "📁 验证部署环境..."
if [ ! -f "deploy/nginx-app.conf" ]; then
    echo "❌ 错误: 找不到 Nginx 配置文件"
    exit 1
fi
echo "✅ 部署文件验证通过"

# 2. 创建应用数据目录（CI/CD 部署的容器需要）
echo "📁 创建应用数据目录..."
mkdir -p data logs
chmod 755 data logs
echo "✅ 数据目录创建完成: $(pwd)/data $(pwd)/logs"

# 3. 创建 Nginx 日志目录
echo "📁 创建 Nginx 日志目录..."
sudo mkdir -p /var/log/nginx
echo "✅ Nginx 日志目录准备完成"

# 4. 备份现有 Nginx 配置
echo "💾 备份现有 Nginx 配置..."
if [ -f "/etc/nginx/sites-available/app.conf" ]; then
    sudo cp /etc/nginx/sites-available/app.conf /etc/nginx/sites-available/app.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ 现有配置已备份"
fi

# 5. 部署 Nginx 反向代理配置
echo "⚙️ 部署 Nginx 反向代理配置..."
sudo cp deploy/nginx-app.conf /etc/nginx/sites-available/app.conf
echo "✅ Nginx 配置文件部署完成"

# 6. 启用反向代理站点
echo "🔗 启用反向代理站点..."
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf
sudo rm -f /etc/nginx/sites-enabled/default
echo "✅ 反向代理站点已启用，默认站点已禁用"

# 7. 测试 Nginx 配置语法
echo "🧪 测试 Nginx 配置..."
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置语法正确"
else
    echo "❌ Nginx 配置语法错误，请检查"
    exit 1
fi

# 8. 重新加载 Nginx
echo "🔄 重新加载 Nginx..."
sudo systemctl reload nginx
echo "✅ Nginx 重新加载完成"

# 9. 验证 Nginx 状态
echo "📊 检查 Nginx 运行状态..."
sudo systemctl status nginx --no-pager | head -8
echo "✅ Nginx 状态正常"

# 10. 检查端口监听
echo "🔍 检查端口监听..."
echo "端口 80 监听情况:"
sudo ss -tlnp | grep :80 || echo "  警告: 端口 80 未监听"
echo "端口 8000 监听情况:"
sudo ss -tlnp | grep :8000 || echo "  提示: 端口 8000 将由 CI/CD 部署的容器监听"

echo ""
echo "🎉 基础设施配置完成！"
echo "======================================================="
echo "📋 配置结果:"
echo "  ✅ Nginx 反向代理: 80端口 → 8000端口"
echo "  ✅ 数据目录: $(pwd)/data"
echo "  ✅ 日志目录: $(pwd)/logs"
echo ""
echo "📋 后续步骤:"
echo "  1. 你的 CI/CD 流水线会自动部署应用到 8000 端口"
echo "  2. 运行验证: bash deploy/verify.sh"
echo "  3. GitHub Webhook 测试: http://3.35.106.116/github_webhook"
echo ""
echo "🚀 现在可以推送代码触发 CI/CD 部署了！"
