#!/bin/bash

# EC2 Nginx 反向代理配置脚本
# 在你的 EC2 服务器上以 sudo 权限执行这些命令

echo "=== 配置 Nginx 反向代理 ==="

# 1. 检查 Nginx 状态
echo "1. 检查 Nginx 当前状态..."
sudo systemctl status nginx

# 2. 备份现有配置
echo "2. 备份现有配置..."
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# 3. 创建 rate limiting 配置（需要添加到 nginx.conf 的 http 块中）
echo "3. 检查并添加 rate limiting 配置..."

# 检查是否已经存在 webhook_limit zone
if ! grep -q "webhook_limit" /etc/nginx/nginx.conf; then
    echo "添加 rate limiting 配置到 nginx.conf..."
    sudo sed -i '/http {/a\\tlimit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=5r/s;' /etc/nginx/nginx.conf
else
    echo "Rate limiting 配置已存在，跳过..."
fi

# 4. 删除默认配置（如果存在）
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

    # Rate limiting for webhook endpoints
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
        
        # GitHub specific headers passthrough
        proxy_set_header X-GitHub-Event $http_x_github_event;
        proxy_set_header X-GitHub-Delivery $http_x_github_delivery;
        proxy_set_header X-Hub-Signature $http_x_hub_signature;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    location /notion_webhook {
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
        
        # Notion specific headers passthrough
        proxy_set_header X-Notion-Signature $http_x_notion_signature;
        
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    location /gitee_webhook {
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
        
        # Gitee specific headers passthrough
        proxy_set_header X-Gitee-Token $http_x_gitee_token;
        proxy_set_header X-Gitee-Event $http_x_gitee_event;
        
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

    location /redoc {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Admin endpoints with authentication
    location /replay-deadletters {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
        proxy_send_timeout 120s;
    }

    # Default location - catch all other requests
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
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml
        text/plain
        text/css
        text/js
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
    echo "Nginx 配置测试通过"
    
    # 8. 重新加载 Nginx
    echo "8. 重新加载 Nginx..."
    sudo systemctl reload nginx
    
    echo "9. 检查 Nginx 状态..."
    sudo systemctl status nginx
    
    echo ""
    echo "=== 配置完成! ==="
    echo "请执行以下测试命令:"
    echo "curl -i http://3.35.106.116/health"
    echo "curl -i http://localhost/health"
    echo ""
    echo "如果返回 200 OK，则配置成功"
    echo "然后可以在 GitHub Webhook 页面点击 'Redeliver' 测试"
else
    echo "Nginx 配置测试失败，请检查配置"
    exit 1
fi 