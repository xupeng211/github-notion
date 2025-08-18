# 生产环境部署指南

## 环境变量配置

在生产环境中，请确保配置以下环境变量：

```bash
# Flask 应用配置
FLASK_ENV=production
FLASK_DEBUG=0
HOST=0.0.0.0
PORT=8787

# 日志配置
LOG_LEVEL=INFO

# Notion API 配置
NOTION_API_TOKEN=your_notion_api_token
NOTION_DATABASE_ID=your_notion_database_id
NOTION_API_VERSION=2022-06-28

# Gitee Webhook 配置
GITEE_WEBHOOK_SECRET=your_gitee_webhook_secret

# 应用环境
ENVIRONMENT=production

# Gunicorn 配置
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
GUNICORN_KEEP_ALIVE=5
```

## AWS 部署检查清单

### 1. 安全配置
- [ ] 使用 AWS Secrets Manager 存储敏感信息
- [ ] 配置适当的安全组规则
- [ ] 启用 HTTPS/SSL
- [ ] 设置 WAF 规则（可选）

### 2. 监控配置
- [ ] 设置 CloudWatch 日志组
- [ ] 配置 CloudWatch 告警
  - CPU 使用率
  - 内存使用率
  - 错误率
  - 响应时间
- [ ] 设置应用健康检查
- [ ] 配置 SNS 通知（可选）

### 3. 备份策略
- [ ] 配置数据备份计划
- [ ] 设置备份保留策略
- [ ] 测试恢复流程

### 4. 扩展配置
- [ ] 配置自动扩展规则（如果需要）
- [ ] 设置负载均衡器（如果需要）
- [ ] 配置多可用区部署（推荐）

### 5. 性能优化
- [ ] 配置 Gunicorn 工作进程数（建议：CPU核心数 * 2 + 1）
- [ ] 优化内存限制
- [ ] 配置缓存策略（如果需要）

### 6. 日志管理
- [ ] 配置日志轮转
- [ ] 设置日志保留期
- [ ] 配置日志分析（可选）

## 部署步骤

1. 准备环境：
   ```bash
   # 创建生产环境配置文件
   cp .env.example .env.production
   # 编辑配置文件，填入实际的生产环境值
   vim .env.production
   ```

2. 构建 Docker 镜像：
   ```bash
   docker build -t gitee-notion-sync:prod .
   ```

3. 测试 Docker 镜像：
   ```bash
   docker run --env-file .env.production -p 8787:8787 gitee-notion-sync:prod
   ```

4. 推送到 AWS ECR：
   ```bash
   # 登录到 ECR
   aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com

   # 标记镜像
   docker tag gitee-notion-sync:prod your-account-id.dkr.ecr.your-region.amazonaws.com/gitee-notion-sync:prod

   # 推送镜像
   docker push your-account-id.dkr.ecr.your-region.amazonaws.com/gitee-notion-sync:prod
   ```

5. 部署到 ECS/EKS：
   - 使用 AWS Console 或 CLI 创建任务定义
   - 配置服务和集群
   - 部署应用

## 健康检查

应用提供了 `/health` 端点用于健康检查，返回以下信息：
- 应用状态
- 环境信息
- Notion API 连接状态
- 时间戳

## 故障排除

1. 如果应用无法启动：
   - 检查环境变量是否正确配置
   - 检查日志输出
   - 验证 Notion API 令牌是否有效

2. 如果健康检查失败：
   - 检查 Notion API 连接
   - 验证应用日志
   - 确认网络配置

3. 如果遇到性能问题：
   - 检查 Gunicorn 配置
   - 监控资源使用情况
   - 分析应用日志

## 维护

1. 定期任务：
   - 检查日志
   - 监控性能指标
   - 更新依赖
   - 检查安全更新

2. 备份：
   - 定期验证备份
   - 测试恢复流程
   - 更新备份策略

3. 安全：
   - 定期更新密钥
   - 检查安全组规则
   - 更新 SSL 证书
