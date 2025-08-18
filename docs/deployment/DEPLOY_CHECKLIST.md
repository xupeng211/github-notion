# 🚀 CI/CD 部署启动检查清单

## ✅ 系统准备就绪确认

### 1. 📋 基础环境检查

#### 必需软件
- [ ] **Git**: 版本控制
  ```bash
  git --version
  ```
- [ ] **Docker**: 容器运行时
  ```bash
  docker --version
  docker-compose --version
  ```
- [ ] **Python 3.11+**: 开发环境
  ```bash
  python3 --version
  ```
- [ ] **curl**: 健康检查工具
  ```bash
  curl --version
  ```

#### 权限检查
- [ ] Docker 守护进程运行中
  ```bash
  docker ps
  ```
- [ ] 脚本有执行权限
  ```bash
  ls -la scripts/
  ```

### 2. 🔧 环境变量配置

#### 必需变量 (生产环境)
```bash
# 复制到 .env 文件或设置为环境变量
export GITEE_WEBHOOK_SECRET="your-webhook-secret"
export NOTION_TOKEN="secret_your-notion-token"
export NOTION_DATABASE_ID="your-database-id"
export DEADLETTER_REPLAY_TOKEN="secure-admin-token"
```

#### 镜像仓库配置 (可选)
```bash
export REGISTRY="your-registry.com"
export REGISTRY_USERNAME="your-username"
export REGISTRY_PASSWORD="your-password"
export IMAGE_NAME="gitee-notion-sync"
```

#### 监控配置 (可选)
```bash
export GRAFANA_PASSWORD="secure-grafana-password"
export GRAFANA_SECRET_KEY="grafana-secret-key"
```

### 3. 🎯 快速启动测试

#### 步骤 1: 验证脚本
```bash
# 检查脚本帮助
./scripts/quick_deploy.sh --help
./scripts/deploy.sh --help
```

#### 步骤 2: 模拟部署测试
```bash
# 测试配置正确性
./scripts/deploy.sh --dry-run staging
```

#### 步骤 3: 构建镜像 (本地测试)
```bash
# 仅构建镜像，不部署
./scripts/quick_deploy.sh --build-only --skip-tests
```

#### 步骤 4: 部署到开发环境
```bash
# 部署到本地开发环境
./scripts/quick_deploy.sh -e dev
```

### 4. 🌟 完整部署流程

#### 预发布环境部署
```bash
# 1. 完整流程部署到预发布
./scripts/quick_deploy.sh -e staging

# 2. 启用监控
./scripts/quick_deploy.sh -e staging -m

# 3. 验证服务
curl http://localhost:8002/health
curl http://localhost:8002/docs
```

#### 生产环境部署
```bash
# 1. 备份并部署
./scripts/deploy.sh --backup production

# 2. 启用完整监控栈
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# 3. 验证生产服务
curl http://localhost:8000/health
```

### 5. 📊 监控验证

#### 检查服务状态
```bash
# 查看容器状态
docker ps

# 查看服务日志
docker-compose -f docker-compose.production.yml logs app

# 查看资源使用
docker stats
```

#### 访问监控界面
- **应用服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/您设置的密码)

### 6. 🔄 CI/CD 流水线测试

#### Git 工作流测试
```bash
# 1. 创建功能分支
git checkout -b feature/ci-cd-test

# 2. 提交测试更改
echo "# CI/CD Test" >> TEST.md
git add TEST.md
git commit -m "test: CI/CD pipeline test"

# 3. 推送触发流水线 (如果配置了远程仓库)
git push origin feature/ci-cd-test
```

#### 手动触发流水线
```bash
# 使用增强版流水线配置
# 在 Gitee Go 平台手动运行 .workflow/enhanced-pipeline.yml
```

### 7. 🚨 故障排查清单

#### 常见问题检查
- [ ] **端口冲突**: 8000, 8002, 9090, 3000 端口是否被占用
- [ ] **磁盘空间**: 至少 2GB 可用空间用于镜像
- [ ] **内存资源**: 至少 2GB 内存用于容器运行
- [ ] **网络连接**: 能够访问 Docker Hub 和 镜像仓库

#### 调试命令
```bash
# 检查 Docker 状态
sudo systemctl status docker

# 查看详细错误日志
docker-compose -f docker-compose.production.yml logs --tail 100

# 重启所有服务
docker-compose -f docker-compose.production.yml restart

# 清理并重新部署
docker-compose -f docker-compose.production.yml down
./scripts/quick_deploy.sh -e production
```

## 🎉 准备完成检查

当您完成以上所有检查项后，您的企业级 CI/CD 系统就完全可以投入使用了！

### 📞 技术支持

如果遇到问题，请检查：
1. **CICD_GUIDE.md** - 完整使用指南
2. **脚本日志输出** - 详细错误信息
3. **Docker 容器日志** - 服务运行状态
4. **监控面板** - Grafana 仪表板

---

✨ **恭喜！您现在拥有了一套完整的企业级 CI/CD 解决方案！**
