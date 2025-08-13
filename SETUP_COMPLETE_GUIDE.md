# 🚀 企业级 CI/CD 完整配置指南

## 📋 当前状态分析

从您的 GitHub Actions 截图可以看到，CI/CD 流水线正在运行但遇到了一些失败。这是正常的，因为我们还需要完成关键配置。

## 🎯 需要完成的 5 个关键步骤

### 步骤 1: 🔑 配置 GitHub Secrets

**立即访问**: https://github.com/xupeng211/github-notion/settings/secrets/actions

**必需的 Secrets**:

```
1. AWS_PRIVATE_KEY
   值: 您的 AWS EC2 私钥文件完整内容 (.pem 文件)
   重要性: ⭐⭐⭐⭐⭐ (必需用于 SSH 连接)

2. GITEE_WEBHOOK_SECRET  
   值: gitee-webhook-secret-2024
   重要性: ⭐⭐⭐⭐⭐ (必需用于验证 webhook)

3. NOTION_TOKEN (可选)
   值: secret_your-notion-integration-token
   重要性: ⭐⭐⭐ (Notion 集成需要)

4. NOTION_DATABASE_ID (可选)
   值: your-notion-database-id
   重要性: ⭐⭐⭐ (Notion 数据库 ID)

5. DEADLETTER_REPLAY_TOKEN
   值: admin-secure-token-$(date +%s)
   重要性: ⭐⭐ (管理功能)

6. GRAFANA_PASSWORD
   值: admin123secure
   重要性: ⭐⭐ (监控面板)
```

### 步骤 2: 🌐 配置 AWS 安全组

**访问 AWS 控制台**: https://console.aws.amazon.com/ec2/

**需要开放的端口**:
```bash
# 在您的 EC2 实例安全组中添加以下规则:

端口 22   (SSH)     源: 0.0.0.0/0  或 您的IP
端口 8000 (HTTP)    源: 0.0.0.0/0  
端口 9090 (监控)    源: 您的IP    (可选)
端口 3000 (Grafana) 源: 您的IP    (可选)
```

### 步骤 3: 🔧 替换 GitHub Actions 工作流

**当前问题**: 原始工作流配置有一些兼容性问题

**解决方案**: 使用修复版工作流

```bash
# 在您的本地环境执行:
rm .github/workflows/deploy.yml
mv .github/workflows/deploy-fixed.yml .github/workflows/deploy.yml
```

### 步骤 4: 🚀 重新触发部署

**方法 1**: 推送新的提交
```bash
git add .
git commit -m "fix: 修复 CI/CD 配置问题"
git push github main
```

**方法 2**: 手动触发 (推荐)
```
1. 访问: https://github.com/xupeng211/github-notion/actions
2. 选择 "CI/CD Pipeline - Fixed Version"
3. 点击 "Run workflow"
4. 选择 main 分支
5. 设置 "Deploy to AWS server" 为 true
6. 点击 "Run workflow"
```

### 步骤 5: 📊 验证部署成功

**等待流水线完成** (约 8-10 分钟)

**验证步骤**:
```bash
# 1. 检查 GitHub Actions 状态 (应该全绿)
# 2. 访问以下地址验证服务:

健康检查: http://3.35.106.116:8000/health
API 文档:  http://3.35.106.116:8000/docs
监控指标: http://3.35.106.116:8000/metrics

# 3. SSH 到服务器检查
ssh -i your-key.pem ubuntu@3.35.106.116
cd /opt/gitee-notion-sync
docker-compose ps
```

## 🔧 故障排查

### 问题 1: SSH 连接失败
```bash
解决方案:
1. 确认 AWS_PRIVATE_KEY secret 格式正确
2. 检查 EC2 实例状态 (running)
3. 验证安全组 SSH 端口 22 开放
4. 确认服务器 IP: 3.35.106.116
```

### 问题 2: Docker 构建失败
```bash
解决方案:
1. 检查 requirements.txt 依赖
2. 验证 Dockerfile 语法
3. 查看 GitHub Actions 详细日志
4. 确认 GitHub Container Registry 权限
```

### 问题 3: 健康检查失败
```bash
解决方案:
1. 检查端口 8000 是否开放
2. 验证容器是否正常启动
3. 查看应用日志: docker-compose logs app
4. 检查防火墙设置
```

## 📈 成功指标

**CI/CD 成功标志**:
- ✅ GitHub Actions 4 个阶段全部绿色
- ✅ Docker 镜像推送到 ghcr.io/xupeng211/gitee-notion:latest
- ✅ AWS 服务器健康检查返回 200
- ✅ API 文档页面可访问

**业务功能验证**:
```bash
# 测试 Webhook 接收 (在服务器上)
curl -X POST http://localhost:8000/gitee_webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitee-Event: Issue Hook" \
  -H "X-Gitee-Token: your-signature" \
  -d '{"action": "open", "issue": {"number": 1, "title": "test"}}'
```

## 🎯 下一步计划

### 1. **完成基础部署** (今天)
- 配置所有必需的 secrets
- 重新触发 CI/CD 流水线
- 验证服务正常运行

### 2. **配置 Gitee Webhook** (今天)
```bash
Gitee 仓库设置 → Webhooks → 添加 Webhook
URL: http://3.35.106.116:8000/gitee_webhook
密钥: gitee-webhook-secret-2024
事件: Issues
```

### 3. **配置 Notion 集成** (可选)
- 创建 Notion Integration
- 获取 API Token 和 Database ID
- 更新 GitHub Secrets

### 4. **启用监控** (推荐)
```bash
# 启动完整监控栈
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# 访问监控面板
Grafana: http://3.35.106.116:3000 (admin/admin123secure)
Prometheus: http://3.35.106.116:9090
```

### 5. **生产优化** (后续)
- 配置域名和 SSL 证书
- 设置数据库备份
- 配置日志聚合
- 性能调优

## 🆘 紧急联系

如果遇到问题，请检查:
1. **GitHub Actions 日志** - 详细错误信息
2. **AWS 控制台** - EC2 实例状态
3. **服务器日志** - SSH 登录检查
4. **网络连接** - 端口和防火墙

---

## 🎉 完成后的成果

配置完成后，您将拥有:
- ✅ **全自动化 CI/CD 流水线**
- ✅ **企业级 Docker 镜像管理**
- ✅ **AWS 云端生产环境**
- ✅ **实时监控和告警**
- ✅ **健康检查和故障恢复**
- ✅ **安全的 Webhook 处理**

**每次推送代码到 main 分支，都会自动触发完整的测试、构建、部署流程！** 