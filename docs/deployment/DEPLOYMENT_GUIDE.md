# GitHub ↔ Notion 双向同步服务部署指南

> **更新说明**: 此指南基于最新架构修复，解决了数据库迁移冲突、异步架构不一致等问题。

## 📋 部署前检查清单

### ✅ 系统要求
- [ ] Python 3.8+
- [ ] 可用磁盘空间 > 2GB
- [ ] 网络访问：GitHub API、Notion API
- [ ] （推荐）反向代理：Nginx/Cloudflare

### ✅ 必需环境变量
- [ ] `GITHUB_TOKEN` - GitHub Personal Access Token
- [ ] `NOTION_TOKEN` - Notion Integration Token
- [ ] `NOTION_DATABASE_ID` - 目标 Notion 数据库 ID

### ✅ 推荐环境变量
- [ ] `GITHUB_WEBHOOK_SECRET` - GitHub Webhook 签名密钥
- [ ] `NOTION_WEBHOOK_SECRET` - Notion Webhook 签名密钥
- [ ] `DEADLETTER_REPLAY_TOKEN` - 死信队列管理令牌

## 🚀 快速部署

### 方法一：使用自动化脚本（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd github-notion-sync

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp env.example .env
# 编辑 .env 文件，填入真实的令牌值

# 4. 使用自动化启动脚本
python scripts/start_service.py
```

### 方法二：手动部署

```bash
# 1. 配置环境变量
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export NOTION_TOKEN="secret_xxxxxxxxxxxx"
export NOTION_DATABASE_ID="xxxxxxxxxxxxxxxx"
export DB_URL="sqlite:///data/sync.db"

# 2. 初始化数据库
python scripts/init_db.py

# 3. 启动服务
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

## 🔐 安全配置指南

### GitHub Token 配置

1. 访问 [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 选择权限：
   - ✅ `repo` - 访问仓库
   - ✅ `issues` - 管理 Issues
   - ✅ `pull_requests` - 管理 PR
4. 复制生成的 token

### Notion Integration 配置

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击 "New integration"
3. 设置集成名称和工作区
4. 复制 "Internal Integration Token"
5. **重要**: 在目标数据库页面，点击右上角 "Share"，邀请你的集成

### 数据库 ID 获取

```bash
# 从 Notion 数据库 URL 提取
# URL: https://notion.so/your-database-id?v=...
# Database ID: your-database-id (32位十六进制字符串)
```

## 🏗️ 生产环境部署

### AWS EC2 部署

```bash
# 1. 连接到 EC2 实例
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. 安装依赖
sudo apt update
sudo apt install python3 python3-pip nginx

# 3. 克隆项目
git clone <repository-url>
cd github-notion-sync

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 配置环境变量
sudo tee /etc/environment << EOF
GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
NOTION_TOKEN="secret_xxxxxxxxxxxx"
NOTION_DATABASE_ID="xxxxxxxxxxxxxxxx"
DB_URL="sqlite:///data/sync.db"
ENVIRONMENT="production"
EOF

# 6. 创建系统服务
sudo tee /etc/systemd/system/github-notion-sync.service << EOF
[Unit]
Description=GitHub-Notion Sync Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/github-notion-sync
Environment=PATH=/home/ubuntu/github-notion-sync/venv/bin
EnvironmentFile=/etc/environment
ExecStart=/home/ubuntu/github-notion-sync/venv/bin/python scripts/start_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable github-notion-sync
sudo systemctl start github-notion-sync
```

### 使用 AWS Systems Manager Parameter Store

```bash
# 存储敏感配置
aws ssm put-parameter \
  --name "/github-notion-sync/github-token" \
  --value "ghp_xxxxxxxxxxxx" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/github-notion-sync/notion-token" \
  --value "secret_xxxxxxxxxxxx" \
  --type "SecureString"

# 在启动脚本中读取
#!/bin/bash
export GITHUB_TOKEN=$(aws ssm get-parameter --name "/github-notion-sync/github-token" --with-decryption --query 'Parameter.Value' --output text)
export NOTION_TOKEN=$(aws ssm get-parameter --name "/github-notion-sync/notion-token" --with-decryption --query 'Parameter.Value' --output text)
python scripts/start_service.py
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 初始化数据库并启动服务
CMD ["python", "scripts/start_service.py"]
```

```bash
# 构建和运行
docker build -t github-notion-sync .
docker run -d \
  --name github-notion-sync \
  -p 8000:8000 \
  -e GITHUB_TOKEN="ghp_xxxxxxxxxxxx" \
  -e NOTION_TOKEN="secret_xxxxxxxxxxxx" \
  -e NOTION_DATABASE_ID="xxxxxxxxxxxxxxxx" \
  -v $(pwd)/data:/app/data \
  github-notion-sync
```

## 🌐 Webhook 配置

### GitHub Webhook

1. 进入你的 GitHub 仓库
2. Settings → Webhooks → Add webhook
3. 配置：
   - **Payload URL**: `https://your-domain.com/github_webhook`
   - **Content type**: `application/json`
   - **Secret**: 你的 `GITHUB_WEBHOOK_SECRET`
   - **Events**: 选择 "Issues"

### Notion Webhook

```bash
# Notion webhook 需要通过 API 配置
curl -X POST 'https://api.notion.com/v1/webhooks' \
  -H 'Authorization: Bearer secret_xxxxxxxxxxxx' \
  -H 'Content-Type: application/json' \
  -H 'Notion-Version: 2022-06-28' \
  -d '{
    "url": "https://your-domain.com/notion_webhook",
    "database_id": "your-database-id"
  }'
```

## 🔍 监控和维护

### 健康检查

```bash
# 基础健康检查
curl http://your-domain:8000/health

# 详细健康检查响应示例
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "environment": "production",
  "app_info": {
    "app": "fastapi",
    "log_level": "INFO",
    "version": "1.0.0"
  },
  "checks": {
    "database": {"status": "ok", "message": "Database connection successful"},
    "notion_api": {"status": "ok", "message": "Notion API connection successful", "database_accessible": true},
    "github_api": {"status": "ok", "message": "GitHub API connection successful", "rate_limit": {"remaining": 4500, "limit": 5000}},
    "disk_space": {"status": "ok", "message": "磁盘空间充足: 15.2GB 可用"},
    "deadletter_queue": {"status": "ok", "message": "死信队列: 0 条记录"}
  }
}
```

### Prometheus 监控

```bash
# Prometheus 指标端点
curl http://your-domain:8000/metrics
```

监控指标包括：
- `events_total` - 事件处理总数
- `process_latency_seconds` - 处理延迟
- `deadletter_size` - 死信队列大小
- `notion_api_calls_total` - Notion API 调用统计
- `rate_limit_hits_total` - 速率限制触发次数

### 死信队列管理

```bash
# 手动重试死信队列
curl -X POST http://your-domain:8000/replay-deadletters \
  -H "Authorization: Bearer your-deadletter-replay-token"
```

### 日志管理

```bash
# 查看系统服务日志
sudo journalctl -u github-notion-sync -f

# 查看应用日志
tail -f logs/app.log
```

## 🚨 故障排除

### 常见问题

**问题**: 服务启动失败，数据库错误
```bash
# 解决方案
python scripts/init_db.py
```

**问题**: Notion API 403 错误
```bash
# 检查 Integration 是否有数据库访问权限
curl -H "Authorization: Bearer $NOTION_TOKEN" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/databases/$NOTION_DATABASE_ID
```

**问题**: GitHub API 速率限制
```bash
# 检查当前限制状态
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     https://api.github.com/rate_limit
```

### 性能优化

1. **数据库优化**
   ```bash
   # 生产环境建议使用 PostgreSQL
   export DB_URL="postgresql://user:password@localhost:5432/sync_db"
   ```

2. **速率限制配置**
   ```bash
   export RATE_LIMIT_PER_MINUTE=60
   ```

3. **日志级别调整**
   ```bash
   export LOG_LEVEL=WARNING  # 生产环境
   ```

## 📱 部署验证

部署完成后，运行验证脚本：

```bash
python scripts/validate_fixes.py
```

成功部署的标志：
- ✅ 所有架构验证测试通过
- ✅ 健康检查返回 "healthy" 状态
- ✅ Webhook 端点响应正常
- ✅ 监控指标可访问

## 🔄 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to EC2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
        run: |
          # SSH 到服务器并部署
          ssh -i ${{ secrets.EC2_KEY }} ubuntu@${{ secrets.EC2_HOST }} << 'EOF'
            cd github-notion-sync
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            python scripts/validate_fixes.py
            sudo systemctl restart github-notion-sync
          EOF
```

## 📞 技术支持

如遇部署问题，请检查：
1. 📋 环境变量配置是否正确
2. 🔐 API 令牌权限是否充足
3. 🌐 网络连接是否正常
4. 💾 磁盘空间是否充足
5. 📊 通过 `/health` 端点查看详细状态

---

**重要提醒**: 所有架构问题已修复，按此指南部署可确保服务稳定运行。
