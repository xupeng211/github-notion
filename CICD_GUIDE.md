# 🚀 CI/CD 流水线部署指南

## 📋 概述

本项目提供了完整的 CI/CD 解决方案，支持从代码提交到生产部署的自动化流水线。

## 🏗️ 架构概览

```
Git Push → CI/CD Pipeline → Docker Build → Registry → Deploy → Monitor
    ↓           ↓              ↓           ↓         ↓        ↓
  代码检查    质量测试        镜像构建      推送      部署    监控告警
```

## 📁 文件结构

```
.
├── .workflow/
│   ├── master-pipeline.yml        # 原有 CI/CD 配置
│   └── enhanced-pipeline.yml      # 增强版 CI/CD 配置
├── scripts/
│   ├── deploy.sh                  # 高级部署脚本
│   └── quick_deploy.sh            # 快速部署脚本
├── monitoring/
│   ├── prometheus-prod.yml        # Prometheus 配置
│   ├── alert_rules.yml            # 告警规则
│   └── grafana/                   # Grafana 配置
├── docker-compose.staging.yml     # 预发布环境配置
├── docker-compose.production.yml  # 生产环境配置
├── Dockerfile                     # 原 Dockerfile
└── Dockerfile.optimized           # 优化版 Dockerfile
```

## 🚀 快速开始

### 1. 本地开发部署
```bash
# 快速部署到 staging 环境
./scripts/quick_deploy.sh

# 仅构建镜像
./scripts/quick_deploy.sh --build-only

# 部署到生产环境并启用监控
./scripts/quick_deploy.sh -e production -m
```

### 2. 服务器部署
```bash
# 部署到预发布环境
./scripts/deploy.sh staging

# 部署指定版本到生产环境
./scripts/deploy.sh -v v1.2.3 production

# 回滚生产环境
./scripts/deploy.sh --rollback production
```

## 🔧 详细配置

### CI/CD 流水线阶段

#### 1. 代码质量检查与测试
- **代码风格检查**: flake8, mypy
- **安全扫描**: bandit
- **单元测试**: pytest + 覆盖率报告
- **数据库迁移测试**: Alembic 验证

#### 2. Docker 镜像构建
- **多阶段构建**: 优化镜像大小
- **安全扫描**: Trivy 容器扫描
- **冒烟测试**: 快速功能验证
- **多标签推送**: version, latest, timestamp

#### 3. 部署验证
- **健康检查**: 深度服务状态检查
- **性能测试**: API 响应时间验证
- **自动回滚**: 部署失败自动恢复

### 环境配置

#### 开发环境 (dev)
- **端口**: 8001
- **配置**: `docker-compose.dev.yml`
- **特点**: 热重载，调试模式

#### 预发布环境 (staging)
- **端口**: 8002
- **配置**: `docker-compose.staging.yml`
- **特点**: 生产镜像，测试配置

#### 生产环境 (production)
- **端口**: 8000
- **配置**: `docker-compose.production.yml`
- **特点**: 资源限制，安全加固，监控告警

## 📊 监控告警

### Prometheus 指标
```yaml
# 服务可用性
up{job="gitee-notion-sync"}

# HTTP 请求指标
rate(http_requests_total[5m])
histogram_quantile(0.95, http_request_duration_seconds_bucket[5m])

# 业务指标
rate(webhook_errors_total[5m])
rate(notion_api_calls_total[5m])
deadletter_size
```

### 告警规则
- **服务下线**: 1分钟无响应
- **错误率过高**: 5xx 错误超过 10%
- **响应缓慢**: P95 响应时间超过 5 秒
- **资源不足**: CPU/内存使用率超过 80%

### Grafana 仪表板
访问 `http://localhost:3000` 查看监控面板:
- 服务概览
- HTTP 请求统计
- Notion API 性能
- 系统资源使用

## 🔐 安全配置

### 容器安全
- **非 root 用户**: 所有容器以 appuser 运行
- **只读文件系统**: 最小权限原则
- **安全选项**: no-new-privileges
- **资源限制**: CPU/内存限制

### 镜像安全
- **漏洞扫描**: Trivy 安全检查
- **最小化镜像**: 多阶段构建
- **签名验证**: 可选的镜像签名

### 网络安全
- **内部网络**: 容器间隔离通信
- **端口限制**: 仅暴露必要端口
- **TLS 终止**: Nginx 反向代理

## 📚 使用示例

### 1. 完整部署流程
```bash
# 1. 开发环境测试
./scripts/quick_deploy.sh -e dev

# 2. 部署到预发布
./scripts/quick_deploy.sh -e staging -m

# 3. 生产环境部署
./scripts/deploy.sh --backup production
```

### 2. 紧急回滚
```bash
# 快速回滚
./scripts/deploy.sh --rollback production

# 或指定版本回滚
./scripts/deploy.sh -v abc123 production
```

### 3. 监控启用
```bash
# 启动完整监控栈
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# 仅启动日志聚合
docker-compose -f docker-compose.production.yml --profile logging up -d
```

## 🔧 环境变量配置

### 必需环境变量
```bash
# 镜像仓库配置
export REGISTRY="your-registry.com"
export REGISTRY_USERNAME="username"
export REGISTRY_PASSWORD="password"
export IMAGE_NAME="gitee-notion-sync"

# 应用配置
export GITEE_WEBHOOK_SECRET="your-secret"
export NOTION_TOKEN="your-token"
export NOTION_DATABASE_ID="your-database-id"

# 管理令牌
export DEADLETTER_REPLAY_TOKEN="admin-token"
export GRAFANA_PASSWORD="secure-password"
```

### 可选配置
```bash
# 安全限制
export RATE_LIMIT_PER_MINUTE="60"
export MAX_REQUEST_SIZE="1048576"

# 监控配置
export GRAFANA_SECRET_KEY="secret-key"
```

## 📝 最佳实践

### 1. 版本管理
- 使用语义化版本 (v1.2.3)
- Git 标签与镜像标签一致
- 保留多个历史版本用于回滚

### 2. 部署策略
- 预发布环境验证
- 蓝绿部署 (可选)
- 灰度发布 (可选)
- 自动化回滚

### 3. 监控运维
- 关键指标告警
- 日志集中收集
- 定期备份
- 容量规划

## 🚨 故障排查

### 常见问题

#### 1. 部署失败
```bash
# 检查服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs app

# 健康检查
curl http://localhost:8000/health
```

#### 2. 监控异常
```bash
# 重启 Prometheus
docker-compose -f docker-compose.production.yml restart prometheus

# 检查配置
docker exec prometheus-prod promtool check config /etc/prometheus/prometheus.yml
```

#### 3. 镜像问题
```bash
# 清理悬空镜像
docker image prune -f

# 重新构建
./scripts/quick_deploy.sh --build-only
```

## 📞 支持与维护

### 日常维护
- 定期更新基础镜像
- 监控磁盘空间
- 备份重要数据
- 审查安全告警

### 扩展功能
- 添加新的监控指标
- 集成更多告警渠道
- 优化构建缓存
- 实现金丝雀部署

---

🎉 **CI/CD 流水线配置完成！** 现在您可以享受全自动化的构建、测试、部署体验。 