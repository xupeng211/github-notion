# 🔧 GitHub 仓库配置指南

## 📋 必需的 GitHub Secrets

请在您的 GitHub 仓库中设置以下 Secrets：

### 1. 🔑 AWS 服务器访问
进入 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret

```
名称: AWS_PRIVATE_KEY
值: 您的 AWS EC2 私钥内容 (.pem 文件的完整内容)
```

### 2. 🌐 应用配置 Secrets

```
名称: GITEE_WEBHOOK_SECRET
值: your-gitee-webhook-secret-here
说明: Gitee Webhook 的密钥，用于验证请求

名称: NOTION_TOKEN
值: secret_your-notion-integration-token
说明: Notion API 集成令牌

名称: NOTION_DATABASE_ID
值: your-notion-database-id
说明: Notion 数据库 ID

名称: DEADLETTER_REPLAY_TOKEN
值: admin-secure-token-123456
说明: 死信重放管理令牌

名称: GRAFANA_PASSWORD
值: admin123secure
说明: Grafana 管理员密码

名称: GRAFANA_SECRET_KEY
值: grafana-secret-key-123456
说明: Grafana 安全密钥
```

## 🚀 部署步骤

### 步骤 1: 准备 AWS 服务器

1. **确保 AWS EC2 实例运行中**
   - 实例地址: `13.209.76.79`
   - 操作系统: Ubuntu 20.04+ 
   - 实例类型: t3.medium 或更高 (推荐)

2. **配置安全组**
   ```bash
   端口 22  (SSH)     - 源: 您的 IP 地址
   端口 8000 (HTTP)   - 源: 0.0.0.0/0 (公网访问)
   端口 9090 (Prometheus) - 源: 您的 IP 地址 (可选)
   端口 3000 (Grafana)    - 源: 您的 IP 地址 (可选)
   ```

3. **测试 SSH 连接**
   ```bash
   ssh -i your-key.pem ubuntu@13.209.76.79
   ```

### 步骤 2: 配置 GitHub 仓库

1. **添加 Secrets** (见上方列表)

2. **启用 GitHub Actions**
   - 进入 Actions 标签页
   - 如果首次使用，点击 "I understand my workflows, go ahead and enable them"

3. **配置 Environment Protection** (可选但推荐)
   ```
   进入 Settings → Environments → New environment
   名称: production
   添加保护规则:
   - Required reviewers: 您自己
   - Deployment protection rules: 启用
   ```

### 步骤 3: 触发部署

#### 方法 1: 推送代码 (自动触发)
```bash
git add .
git commit -m "feat: 添加 GitHub Actions CI/CD 流水线"
git push github main
```

#### 方法 2: 手动触发
```
进入 GitHub 仓库 → Actions → "CI/CD Pipeline - Build & Deploy" → Run workflow
选择分支: main
勾选: Deploy to AWS server
点击: Run workflow
```

## 📊 监控部署进度

### 1. GitHub Actions 界面
- 进入 Actions 标签页查看实时日志
- 4 个阶段: Test → Build & Push → Deploy AWS → Notify

### 2. 部署验证
部署完成后，访问以下地址验证：

```
🏥 健康检查: http://13.209.76.79:8000/health
📚 API 文档:  http://13.209.76.79:8000/docs  
📊 监控指标: http://13.209.76.79:8000/metrics
```

### 3. AWS 服务器检查
```bash
# SSH 到服务器检查状态
ssh -i your-key.pem ubuntu@13.209.76.79

# 检查服务状态
cd /opt/gitee-notion-sync
docker-compose ps
docker-compose logs app
```

## 🔧 故障排查

### 常见问题

#### 1. SSH 连接失败
```bash
# 检查项目
- SSH 密钥文件格式正确
- AWS 安全组开放 22 端口
- 服务器地址正确: 13.209.76.79
```

#### 2. Docker 构建失败
```bash
# 查看 GitHub Actions 日志
- 检查 Dockerfile.optimized 语法
- 确认 requirements.txt 依赖正确
- 查看构建错误详情
```

#### 3. 健康检查失败
```bash
# AWS 服务器上检查
docker-compose logs app
curl http://localhost:8000/health

# 检查端口和防火墙
sudo netstat -tlnp | grep 8000
sudo ufw status
```

#### 4. Secrets 配置错误
```bash
# 重新检查 GitHub Secrets
- 确认所有 Secret 名称正确
- 检查值中没有多余空格
- Notion Token 以 "secret_" 开头
```

## 🎯 成功指标

部署成功的标志：
- ✅ GitHub Actions 所有步骤绿色通过
- ✅ 健康检查返回 200 状态码
- ✅ API 文档页面可访问
- ✅ 服务容器正常运行

## 📞 技术支持

如果遇到问题：
1. 查看 GitHub Actions 详细日志
2. SSH 到服务器检查 Docker 日志
3. 检查 AWS 安全组配置
4. 验证所有 Secrets 设置正确

---

🎉 **配置完成后，您将拥有全自动化的 CI/CD 流水线！** 