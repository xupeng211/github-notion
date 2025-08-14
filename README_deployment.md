# Nginx 反向代理配置部署指南

## 文件说明
- `app.conf`: Nginx 反向代理配置文件
- `deploy_nginx.sh`: 自动部署脚本

## 部署方式

### 方式一：自动部署（推荐）
```bash
# 赋予脚本执行权限
chmod +x deploy_nginx.sh

# 运行自动部署脚本
bash deploy_nginx.sh
```

### 方式二：手动部署

#### 1. 上传配置文件
```bash
scp -i ~/.ssh/Xp13408529631.pem app.conf ubuntu@3.35.106.116:~/app.conf
```

#### 2. SSH 连接服务器
```bash
ssh -i ~/.ssh/Xp13408529631.pem ubuntu@3.35.106.116
```

#### 3. 在服务器上配置 Nginx
```bash
# 移动配置文件到正确位置
sudo cp ~/app.conf /etc/nginx/sites-available/app.conf

# 创建符号链接启用站点
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf

# 删除默认站点（避免冲突）
sudo rm -f /etc/nginx/sites-enabled/default

# 测试 Nginx 配置
sudo nginx -t

# 如果配置测试通过，重新加载 Nginx
sudo systemctl reload nginx

# 检查 Nginx 状态
sudo systemctl status nginx
```

## 测试配置

### 1. 测试健康检查端点
```bash
curl -i http://3.35.106.116/health
```
**预期结果**：返回 HTTP 200 状态码

### 2. 测试根路径
```bash
curl -i http://3.35.106.116/
```

### 3. 测试 GitHub Webhook
1. 前往 GitHub Repository → Settings → Webhooks
2. 找到你的 webhook 配置
3. 点击 "Redeliver" 按钮
4. 查看 Response 应该显示 HTTP 200

### 4. 查看 Nginx 日志（如有问题）
```bash
# 在服务器上查看错误日志
sudo tail -f /var/log/nginx/app_error.log

# 查看访问日志
sudo tail -f /var/log/nginx/app_access.log
```

## 配置说明

### 主要特性
- ✅ 反向代理到 127.0.0.1:8000
- ✅ 支持两个 server_name：`3.35.106.116` 和 `ec2-3-35-106-116.ap-northeast-2.compute.amazonaws.com`
- ✅ 配置 X-Forwarded-* 头信息
- ✅ 专门的健康检查路由 `/health`
- ✅ GitHub Webhook 支持 `/github_webhook`
- ✅ 优化的超时设置
- ✅ 安全头配置

### 路由配置
- `/health` → `127.0.0.1:8000/health` (健康检查)
- `/github_webhook` → `127.0.0.1:8000/github_webhook` (GitHub Webhook)
- `/` → `127.0.0.1:8000/` (所有其他请求)

## 故障排除

### 如果健康检查失败
1. 检查 FastAPI 容器是否在 8000 端口运行：
   ```bash
   docker ps
   curl http://127.0.0.1:8000/health
   ```

2. 检查防火墙设置：
   ```bash
   sudo ufw status
   ```

### 如果 Nginx 配置测试失败
```bash
# 检查配置文件语法
sudo nginx -t

# 查看详细错误信息
sudo nginx -T
```

### 检查端口占用
```bash
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000
``` 