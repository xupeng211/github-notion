# 🚀 部署指南

## 📋 部署概览

本项目支持多种部署方式，推荐使用 Docker 容器化部署。

### 🐳 Docker 部署

#### 本地部署
```bash
# 1. 构建镜像
docker build -f Dockerfile.github -t github-notion:latest .

# 2. 运行容器
docker run -d \
  --name github-notion \
  -p 8000:8000 \
  --env-file .env \
  github-notion:latest
```

#### Docker Compose 部署
```bash
# 1. 配置环境变量
cp .env.template .env
# 编辑 .env 文件

# 2. 启动服务
docker-compose up -d

# 3. 检查状态
docker-compose ps
```

### ☁️ 云平台部署

#### GitHub Actions CI/CD
项目配置了自动化 CI/CD 流程：
- 推送到 main 分支自动触发构建
- 自动构建 Docker 镜像
- 自动部署到目标环境

#### 手动触发部署
1. 进入 GitHub Actions 页面
2. 选择 "Optimized Build and Deploy"
3. 点击 "Run workflow"
4. 选择环境 (production/staging/testing)

### 🔧 环境配置

#### 必需环境变量
```bash
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id
DEADLETTER_REPLAY_TOKEN=your_replay_token
```

#### 可选环境变量
```bash
ENVIRONMENT=production
APP_PORT=8000
LOG_LEVEL=INFO
```

### 🏥 健康检查

#### 健康检查端点
- `/health` - 完整健康检查
- `/health/ci` - CI/CD 专用健康检查

#### 检查命令
```bash
# 标准健康检查
curl http://localhost:8000/health

# CI 健康检查
curl http://localhost:8000/health/ci
```

### 📊 监控

#### 日志查看
```bash
# Docker 容器日志
docker logs github-notion

# Docker Compose 日志
docker-compose logs -f
```

#### 性能监控
- 应用响应时间
- 数据库连接状态
- 磁盘空间使用
- 内存使用情况

### 🔄 更新部署

#### 滚动更新
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建
docker-compose build

# 3. 重启服务
docker-compose up -d
```

#### 零停机更新
使用蓝绿部署或滚动更新策略。

### 🛠️ 故障排除

#### 常见问题
1. **容器启动失败**: 检查环境变量配置
2. **健康检查失败**: 检查应用日志
3. **网络连接问题**: 检查端口配置
4. **权限问题**: 检查文件权限

#### 诊断命令
```bash
# 检查容器状态
docker ps -a

# 检查网络
docker network ls

# 检查日志
docker logs --tail 50 github-notion
```

### 📞 支持

如果遇到部署问题：
1. 查看 `docs/TROUBLESHOOTING.md`
2. 检查应用日志
3. 运行本地测试: `./scripts/test-build-locally.sh`
