# EC2 Nginx 反向代理配置指南

## 📋 操作步骤

### 1. 连接到你的 EC2 服务器
```bash
ssh -i your-key.pem ubuntu@3.35.106.116
```

### 2. 确认 FastAPI 服务运行在 8000 端口
```bash
# 检查服务是否在运行
curl -s http://127.0.0.1:8000/health || echo "FastAPI 服务未运行在 8000 端口"

# 如果服务未运行，启动容器
cd /opt/gitee-notion-sync  # 或你的项目目录
docker-compose up -d
```

### 3. 执行 Nginx 配置脚本

将本地的配置脚本复制到服务器：

**方法一：直接在服务器上创建脚本**
```bash
# 在 EC2 服务器上创建脚本文件
cat > nginx-setup.sh << 'SCRIPT_EOF'
#!/bin/bash

echo "=== 配置 Nginx 反向代理 ==="

# 1. 检查 Nginx 状态
echo "1. 检查 Nginx 当前状态..."
sudo systemctl status nginx --no-pager

# 2. 备份现有配置
echo "2. 备份现有配置..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# 3. 添加 rate limiting 配置
echo "3. 检查并添加 rate limiting 配置..."
if ! grep -q "webhook_limit" /etc/nginx/nginx.conf; then
    echo "添加 rate limiting 配置..."
    sudo sed -i '/http {/a\\tlimit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=5r/s;' /etc/nginx/nginx.conf
else
    echo "Rate limiting 配置已存在"
fi

# 4. 删除默认配置
echo "4. 处理默认配置..."
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
    echo "已移除默认配置"
fi

# 5. 创建应用配置文件
echo "5. 创建应用配置文件..."
sudo tee /etc/nginx/sites-available/app.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name 3.35.106.116 ec2-3-35-106-116.ap-northeast-2.compute.amazonaws.com;

    # Basic security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # GitHub webhook endpoint
    location /github_webhook {
        limit_req zone=webhook_limit burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # GitHub specific headers
        proxy_set_header X-GitHub-Event $http_x_github_event;
        proxy_set_header X-GitHub-Delivery $http_x_github_delivery;
        proxy_set_header X-Hub-Signature $http_x_hub_signature;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 30s;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
    }

    # Metrics endpoint
    location /metrics {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 30s;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Default location
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        application/json
        application/javascript
        text/plain
        text/css
        text/xml
        text/javascript;
}
EOF

# 6. 启用配置
echo "6. 启用配置..."
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/

# 7. 测试配置
echo "7. 测试 Nginx 配置..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx 配置测试通过"
    
    # 8. 重新加载 Nginx
    echo "8. 重新加载 Nginx..."
    sudo systemctl reload nginx
    
    echo "9. 检查 Nginx 状态..."
    sudo systemctl status nginx --no-pager
    
    echo ""
    echo "🎉 配置完成!"
else
    echo "❌ Nginx 配置测试失败"
    exit 1
fi
SCRIPT_EOF

# 给脚本执行权限
chmod +x nginx-setup.sh

# 执行脚本
./nginx-setup.sh
```

### 4. 测试配置

配置完成后，执行以下测试：

```bash
# 测试健康检查
curl -i http://3.35.106.116/health
curl -i http://localhost/health

# 测试 GitHub webhook 端点（会返回 400 因为没有有效 payload）
curl -i -X POST http://3.35.106.116/github_webhook

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

**期望结果：**
- `/health` 返回 `200 OK` 和 JSON 响应
- `/github_webhook` 返回 `400 Bad Request`（正常，因为没有有效 payload）
- Nginx 日志显示请求被代理到 127.0.0.1:8000

### 5. GitHub Webhook 测试

1. 打开你的 GitHub 仓库
2. Settings → Webhooks → 找到你配置的 webhook
3. 点击 **"Redeliver"** 按钮重新发送测试请求
4. 查看 Response 部分，应该显示 `200 OK`

### 6. 故障排查

如果遇到问题：

```bash
# 检查 Nginx 配置语法
sudo nginx -t

# 查看 Nginx 错误日志
sudo tail -n 50 /var/log/nginx/error.log

# 检查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 重启服务
sudo systemctl restart nginx
docker-compose restart  # 重启 FastAPI 服务

# 检查防火墙
sudo ufw status
```

## ✅ 成功标志

- `curl http://3.35.106.116/health` 返回 200 OK
- GitHub Webhook 测试返回 200 OK  
- 可以访问 `http://3.35.106.116/docs` 查看 API 文档
- Nginx 日志显示请求正确代理到后端服务

配置成功后，你的 GitHub Webhook 就能正常接收和处理 Issues 事件了！ 