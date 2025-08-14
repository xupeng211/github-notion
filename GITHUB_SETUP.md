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

名称: NOTION_WEBHOOK_SECRET (可选)
值: your-optional-notion-webhook-secret
说明: Notion Webhook 自定义签名密钥

名称: GITHUB_TOKEN
值: ghp_xxx
说明: GitHub API Token，需最少 repo / issues 权限

名称: GITHUB_WEBHOOK_SECRET
值: strong-random-secret
说明: GitHub Webhook 签名校验密钥

名称: DEADLETTER_REPLAY_TOKEN
值: admin-secure-token-123456
说明: 死信重放管理令牌
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
3. **配置 Environment Protection**（可选）

### 步骤 3: 配置 GitHub Webhook（Issues）

1. 仓库 → Settings → Webhooks → Add webhook
2. Payload URL：`https://<DOMAIN>/github_webhook`
3. Content type：`application/json`
4. Secret：使用 `GITHUB_WEBHOOK_SECRET`
5. 选择 `Let me select individual events` → 勾选 `Issues`
6. 保存后 GitHub 会发送 `ping`/`issues` 测试事件

### 步骤 4: 触发部署

略（与现有流程一致）

## 📊 监控部署进度

略（与现有流程一致）

## 🔧 故障排查

- 403 invalid_signature：检查 `GITHUB_WEBHOOK_SECRET` 是否一致
- 400 invalid_payload：检查事件 `X-GitHub-Event=issues` 与 JSON 格式
- 429 too_many_requests：提升 `RATE_LIMIT_PER_MINUTE` 或限流放宽

## 🎯 成功指标

- `/github_webhook` 接收并返回 200
- Notion 中生成/更新页面
- Notion 更新回写成功（GitHub Issue 有变更）

---

🎉 配置完成后，将获得 GitHub ↔ Notion 的双向同步能力！ 