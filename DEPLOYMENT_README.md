# 🚀 GitHub-Notion 同步系统生产部署指南

## 📋 部署目标
确保 GitHub Webhook 对 `http://3.35.106.116/github_webhook` 的 Ping 返回 200 状态码，并保证项目稳定运行。

---

## ⚡ 快速部署（一键执行）

### 方法一：自动化部署脚本

```bash
# 1. 确保在项目根目录
cd ~/PC

# 2. 运行一键部署脚本
sudo bash deploy/deploy.sh

# 3. 启动 FastAPI 应用（选择其中一种方式）
# 方式 A: 临时启动（测试用）
source .env && export $(grep -v '^#' .env | grep -v '^$' | xargs)
uvicorn app.server:app --host 127.0.0.1 --port 8000

# 方式 B: 使用 systemd（推荐生产环境）
sudo cp deploy/systemd-service.txt /etc/systemd/system/github-notion-sync.service
sudo systemctl daemon-reload
sudo systemctl enable github-notion-sync
sudo systemctl start github-notion-sync

# 4. 运行验证检查
bash deploy/verify.sh
```

---

## 📁 文件结构

```
~/PC/
├── deploy/
│   ├── nginx-app.conf          # Nginx 配置文件
│   ├── deploy.sh              # 一键部署脚本
│   ├── verify.sh              # 一键验证脚本
│   ├── systemd-service.txt    # systemd 服务单元文件
│   └── docker-compose.yml     # Docker Compose 配置（可选）
├── data/                      # SQLite 数据库目录（自动创建）
├── logs/                      # 日志目录（自动创建）
└── .env                       # 环境变量配置
```

---

## 🔧 详细部署步骤

### 1. Nginx 配置部署

#### 复制配置文件
```bash
# 备份现有配置（如果存在）
sudo cp /etc/nginx/sites-available/app.conf /etc/nginx/sites-available/app.conf.backup.$(date +%Y%m%d_%H%M%S)

# 复制新配置
sudo cp deploy/nginx-app.conf /etc/nginx/sites-available/app.conf
```

#### 启用站点配置
```bash
# 创建软链接启用站点
sudo ln -sf /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf

# 禁用默认站点（避免冲突）
sudo rm -f /etc/nginx/sites-enabled/default
```

#### 测试和重载配置
```bash
# 测试配置语法
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx

# 检查 Nginx 状态
sudo systemctl status nginx
```

### 2. 目录结构创建

```bash
# 在项目根目录创建必需目录
mkdir -p data logs
chmod 755 data logs

# 确保 Nginx 日志目录存在
sudo mkdir -p /var/log/nginx
```

### 3. FastAPI 应用部署

#### 方式 A: 使用 systemd（推荐）

```bash
# 创建 systemd 服务单元
sudo tee /etc/systemd/system/github-notion-sync.service << 'EOF'
[Unit]
Description=GitHub-Notion Sync Service
After=network.target
Requires=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/PC
EnvironmentFile=/home/ubuntu/PC/.env
ExecStart=/home/ubuntu/.pyenv/versions/3.11.9/bin/uvicorn app.server:app --host 127.0.0.1 --port 8000 --workers 2
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=github-notion-sync

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/home/ubuntu/PC/data /home/ubuntu/PC/logs
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable github-notion-sync
sudo systemctl start github-notion-sync

# 检查服务状态
sudo systemctl status github-notion-sync
```

#### 方式 B: Docker Compose（可选）

```bash
# 构建并启动容器
docker-compose -f deploy/docker-compose.yml up -d

# 查看容器状态
docker-compose -f deploy/docker-compose.yml ps

# 查看日志
docker-compose -f deploy/docker-compose.yml logs -f github-notion-sync
```

---

## 🧪 验证部署

### 自动化验证

```bash
# 运行一键验证脚本
bash deploy/verify.sh
```

### 手动验证步骤

#### 1. 检查端口监听
```bash
# 检查 80 端口（Nginx）
sudo ss -tlnp | grep :80

# 检查 8000 端口（FastAPI）
sudo ss -tlnp | grep :8000
```

#### 2. 测试服务端点
```bash
# 本地 FastAPI 健康检查
curl -i http://127.0.0.1:8000/health

# Nginx 反向代理健康检查
curl -i http://127.0.0.1/health
curl -i http://3.35.106.116/health

# GitHub Webhook 端点测试
curl -i -X POST http://3.35.106.116/github_webhook \
  -H "Content-Type: application/json" \
  -d '{"zen": "test ping"}'
```

#### 3. 预期响应
- **健康检查**: HTTP 200 状态码 + JSON 响应
- **Webhook 端点**: HTTP 200 或 405（方法不允许，但端点可访问）

---

## 🎯 GitHub Webhook 配置

### 1. 进入 GitHub 仓库设置
- 访问：`https://github.com/你的用户名/仓库名/settings/hooks`

### 2. 配置 Webhook
```
Payload URL: http://3.35.106.116/github_webhook
Content type: application/json
Secret: [你的 GITHUB_WEBHOOK_SECRET]
SSL verification: 暂时禁用（如果使用 HTTP）
Events: Issues, Issue comments
```

### 3. 测试 Webhook
- 点击 "Redeliver" 按钮
- 在 "Recent Deliveries" 查看响应
- **预期结果**: Response: 200 ✅

---

## 📊 监控和日志

### 查看日志
```bash
# Nginx 访问日志
sudo tail -f /var/log/nginx/github_notion_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/github_notion_error.log

# FastAPI 应用日志（systemd）
sudo journalctl -u github-notion-sync -f

# FastAPI 应用日志（Docker）
docker-compose -f deploy/docker-compose.yml logs -f github-notion-sync
```

### 服务管理命令
```bash
# systemd 方式
sudo systemctl status github-notion-sync    # 查看状态
sudo systemctl restart github-notion-sync   # 重启服务
sudo systemctl stop github-notion-sync      # 停止服务
sudo systemctl start github-notion-sync     # 启动服务

# Docker Compose 方式
docker-compose -f deploy/docker-compose.yml ps       # 查看状态
docker-compose -f deploy/docker-compose.yml restart  # 重启服务
docker-compose -f deploy/docker-compose.yml down     # 停止服务
docker-compose -f deploy/docker-compose.yml up -d    # 启动服务
```

---

## 🛠️ 故障排除

### 常见问题及解决方案

#### 1. 端口 8000 无法访问
```bash
# 检查 FastAPI 是否运行
ps aux | grep uvicorn

# 检查端口占用
sudo ss -tlnp | grep :8000

# 重启 FastAPI 服务
sudo systemctl restart github-notion-sync
```

#### 2. Nginx 反向代理失败
```bash
# 检查 Nginx 配置语法
sudo nginx -t

# 查看 Nginx 错误日志
sudo tail -20 /var/log/nginx/error.log

# 重新加载配置
sudo systemctl reload nginx
```

#### 3. GitHub Webhook 返回错误
```bash
# 查看详细的访问日志
sudo tail -f /var/log/nginx/github_notion_access.log

# 检查应用程序日志
sudo journalctl -u github-notion-sync -n 50

# 手动测试 webhook 端点
curl -v -X POST http://127.0.0.1:8000/github_webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

#### 4. 数据库连接错误
```bash
# 检查 data 目录权限
ls -la data/

# 手动创建数据库目录
mkdir -p data && chmod 755 data

# 检查环境变量
grep DB_URL .env
```

### 调试命令集合
```bash
# 完整系统状态检查
echo "=== Nginx 状态 ===" && sudo systemctl status nginx --no-pager
echo "=== FastAPI 状态 ===" && sudo systemctl status github-notion-sync --no-pager
echo "=== 端口监听 ===" && sudo ss -tlnp | grep -E ':(80|8000)'
echo "=== 最近日志 ===" && sudo journalctl -u github-notion-sync -n 10 --no-pager
```

---

## 🎉 部署完成检查清单

- [ ] ✅ Nginx 配置文件部署完成
- [ ] ✅ 站点配置已启用，默认站点已禁用
- [ ] ✅ data/ 目录创建并可写
- [ ] ✅ FastAPI 应用在 8000 端口运行
- [ ] ✅ 本地健康检查返回 200
- [ ] ✅ 反向代理健康检查返回 200
- [ ] ✅ 外网健康检查返回 200
- [ ] ✅ GitHub Webhook 端点可访问
- [ ] ✅ GitHub Webhook 配置完成
- [ ] ✅ Webhook Redeliver 返回 200

---

## 📞 获取帮助

如果遇到问题：
1. 运行 `bash deploy/verify.sh` 查看详细状态
2. 查看相关日志文件
3. 参考故障排除部分
4. 确保防火墙和安全组设置正确

**🎊 祝部署成功！现在你的 GitHub-Notion 双向同步系统已经准备就绪！**
