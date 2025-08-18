# 远程服务器部署配置指南

## 🚀 快速部署配置

### 1. 检查代码更新状态

```bash
# 在远程服务器上拉取最新代码
cd /path/to/your/project
git pull origin main

# 确认最新提交
git log --oneline -3
# 应该看到: 85f6656 📊 Add Service Validation and Test Reports
```

### 2. 配置环境变量

#### 方法一：创建 .env 文件 (推荐)
```bash
# 复制模板文件
cp environment-config.template .env

# 编辑配置文件
nano .env
# 或使用 vi .env

# 填入你的实际配置值
```

#### 方法二：直接设置环境变量
```bash
# 基础配置 (必须)
export GITEE_WEBHOOK_SECRET="your-actual-secret"
export GITHUB_WEBHOOK_SECRET="your-actual-secret"

# API配置 (推荐)
export NOTION_TOKEN="your-notion-token"
export NOTION_DATABASE_ID="your-database-id"

# 功能配置
export DISABLE_NOTION=1          # 暂时禁用Notion
export DISABLE_METRICS=""        # 启用监控
export ENVIRONMENT="production"
```

### 3. 创建必要目录

```bash
# 创建数据目录
mkdir -p data
mkdir -p logs

# 设置权限
chmod 755 data logs
```

## 🎯 部署场景选择

### 场景A：完整功能部署
**适用于：有完整Notion集成需求**

```bash
export GITEE_WEBHOOK_SECRET="your-secret"
export GITHUB_WEBHOOK_SECRET="your-secret"
export NOTION_TOKEN="your-token"
export NOTION_DATABASE_ID="your-db-id"
export DISABLE_NOTION=0
export DISABLE_METRICS=""
export ENVIRONMENT="production"
```

### 场景B：仅Webhook处理 (推荐开始)
**适用于：暂时不需要Notion集成**

```bash
export GITEE_WEBHOOK_SECRET="your-secret"
export GITHUB_WEBHOOK_SECRET="your-secret"
export DISABLE_NOTION=1                     # 禁用Notion
export DISABLE_METRICS=""                   # 启用监控
export ENVIRONMENT="production"
```

### 场景C：调试模式
**适用于：故障排查**

```bash
export GITEE_WEBHOOK_SECRET="your-secret"
export GITHUB_WEBHOOK_SECRET="your-secret"
export DISABLE_NOTION=1
export DISABLE_METRICS=""
export LOG_LEVEL="DEBUG"                    # 详细日志
export ENVIRONMENT="development"
```

## 🔧 服务启动

### 使用Docker (推荐)
```bash
# 构建镜像
docker build -t github-notion-sync .

# 运行容器
docker run -d \
  --name github-notion-sync \
  -p 8000:8000 \
  --env-file .env \
  github-notion-sync
```

### 直接运行
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### 后台运行
```bash
# 使用nohup
nohup uvicorn app.server:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &

# 或使用systemd (更推荐)
sudo systemctl start github-notion-sync
```

## 🔍 健康检查

### 基础检查
```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查监控指标
curl http://localhost:8000/metrics
```

### 功能测试
```bash
# 测试Gitee webhook (需要正确的secret)
curl -X POST http://localhost:8000/gitee_webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitee-Token: your-secret" \
  -H "X-Gitee-Delivery: test-123" \
  -d '{"action":"opened","issue":{"number":1}}'
```

## ⚠️ 常见问题排查

### 问题1：webhook_secret_not_configured
**解决**：确保设置了 `GITEE_WEBHOOK_SECRET` 和 `GITHUB_WEBHOOK_SECRET`

### 问题2：invalid_signature
**解决**：检查webhook secret是否与平台配置一致

### 问题3：Notion API错误
**解决**：设置 `DISABLE_NOTION=1` 暂时禁用

### 问题4：监控指标为空
**解决**：确保 `DISABLE_METRICS` 为空或设为0

## 📊 监控配置

### Prometheus集成
```bash
# 访问指标端点
curl http://localhost:8000/metrics

# 配置Prometheus
# 在prometheus.yml中添加:
scrape_configs:
  - job_name: 'github-notion-sync'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

## 🛡️ 安全建议

1. **使用强密码**：webhook secret应该足够复杂
2. **防火墙配置**：仅开放必要端口
3. **HTTPS部署**：生产环境使用反向代理
4. **定期更新**：及时拉取代码更新
5. **日志监控**：定期检查应用日志
