#!/bin/bash

# Nginx 反向代理配置部署脚本
# 使用方法：bash deploy_nginx.sh

echo "=== Nginx 反向代理配置部署脚本 ==="

# 1. 上传配置文件到服务器
echo "1. 上传配置文件到服务器..."
scp -i ~/.ssh/Xp13408529631.pem app.conf ubuntu@3.35.106.116:~/app.conf

# 2. SSH 到服务器执行配置
echo "2. 连接服务器并配置 Nginx..."
ssh -i ~/.ssh/Xp13408529631.pem ubuntu@3.35.106.116 << 'EOF'

# 移动配置文件到正确位置
sudo cp ~/app.conf /etc/nginx/sites-available/app.conf

# 创建符号链接启用站点
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf

# 删除默认站点（如果存在）
sudo rm -f /etc/nginx/sites-enabled/default

# 测试 Nginx 配置
echo "测试 Nginx 配置..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "Nginx 配置测试通过，重新加载 Nginx..."
    sudo systemctl reload nginx
    echo "Nginx 配置部署完成！"
else
    echo "❌ Nginx 配置测试失败，请检查配置文件"
    exit 1
fi

# 检查 Nginx 状态
echo "检查 Nginx 运行状态..."
sudo systemctl status nginx --no-pager

# 检查端口监听
echo "检查端口监听情况..."
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

echo "=== 配置部署完成 ==="

EOF

echo "=== 测试连接 ==="
echo "等待 2 秒后开始测试..."
sleep 2

# 3. 测试健康检查
echo "3. 测试健康检查端点..."
curl -i http://3.35.106.116/health

echo -e "\n=== 部署和测试完成 ==="
echo "请前往 GitHub Webhook 页面点击 'Redeliver' 测试 webhook 功能" 