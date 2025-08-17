# 🔐 GitHub Secrets 配置指南

## 📋 概述

根据当前 CI/CD 配置分析，你需要在 GitHub 仓库中配置以下 Secrets 来启用完整的部署功能。

## 🎯 **立即需要配置的 Secrets**

### **🔴 必需配置 (部署相关)**

| Secret 名称 | 值来源 | 描述 | 示例 |
|------------|--------|------|------|
| `AWS_PRIVATE_KEY` | EC2 密钥对的 .pem 文件内容 | AWS EC2 SSH 私钥 | `-----BEGIN RSA PRIVATE KEY-----\n...` |
| `GITHUB_WEBHOOK_SECRET` | GitHub Webhook 配置页面 | GitHub webhook 签名密钥 | `your_github_webhook_secret` |
| `NOTION_TOKEN` | Notion Integration 页面 | Notion API 访问令牌 | `secret_xxxxxxxxxxxxxxxxx` |
| `NOTION_DATABASE_ID` | Notion 数据库 URL | 目标 Notion 数据库 ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

### **🟡 可选配置 (增强功能)**

| Secret 名称 | 值来源 | 描述 | 默认值 |
|------------|--------|------|--------|
| `DEADLETTER_REPLAY_TOKEN` | 自定义生成 | 死信队列管理令牌 | 留空 |

## 🚀 **配置步骤**

### 1. 进入 GitHub 仓库设置
```
你的仓库 → Settings → Secrets and variables → Actions → New repository secret
```

### 2. 逐个添加 Secrets

#### **AWS_PRIVATE_KEY**
```bash
# 1. 找到你的 EC2 密钥对文件 (通常是 .pem 文件)
# 2. 复制整个文件内容，包括 BEGIN 和 END 行
# 3. 粘贴到 GitHub Secrets 中

# 文件内容示例：
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...完整的私钥内容...
-----END RSA PRIVATE KEY-----
```

# Gitee webhook removed - focusing on GitHub ↔ Notion sync only

#### **GITHUB_WEBHOOK_SECRET**
```bash
# 1. 进入 GitHub 仓库设置
# 2. Settings → Webhooks → Add webhook
# 3. URL: https://your-domain.com/webhook/github
# 4. 设置 Secret，复制这个密钥到 GitHub Secrets
```

#### **NOTION_TOKEN**
```bash
# 1. 访问 https://www.notion.so/my-integrations
# 2. 创建新的 Integration
# 3. 复制 Internal Integration Token
# 4. 格式：secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### **NOTION_DATABASE_ID**
```bash
# 1. 打开你的 Notion 数据库页面
# 2. 复制页面 URL 中的数据库 ID
# 3. URL 格式：https://notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 4. 数据库 ID 就是 URL 中的那串字符
```

## 🔧 **当前服务器配置**

根据 `deploy.yml` 配置，当前目标服务器信息：
- **服务器 IP**: `3.35.106.116`
- **用户名**: `ubuntu`
- **SSH 端口**: `22`

## ✅ **验证配置**

配置完成后，你可以：

1. **手动触发部署**：
   ```
   GitHub → Actions → 🚀 Production CI/CD Pipeline → Run workflow
   ```

2. **推送代码触发**：
   ```bash
   git push origin main
   ```

3. **检查部署日志**：
   ```
   GitHub → Actions → 查看最新的 workflow 运行
   ```

## 🎯 **优化说明**

### **已完成的优化**
- ✅ 统一使用 `deploy.yml` 作为主要部署流程
- ✅ 禁用 `cd.yml` 避免重复部署
- ✅ 简化 secrets 配置，移除不必要的变量
- ✅ 优化环境变量格式

### **部署流程**
```
推送到 main 分支
    ↓
运行测试 (ci.yml)
    ↓
构建 Docker 镜像
    ↓
推送到 GitHub Container Registry
    ↓
部署到 AWS 服务器 (3.35.106.116)
    ↓
发送部署通知
```

## 🚨 **注意事项**

1. **AWS_PRIVATE_KEY** 必须是完整的 .pem 文件内容
2. **Webhook secrets** 必须与实际配置的 webhook 密钥一致
3. **Notion token** 需要有访问目标数据库的权限
4. 配置完成后，第一次部署可能需要几分钟时间

## 📞 **故障排除**

如果部署失败，检查：
1. Secrets 是否正确配置
2. AWS 服务器是否可访问
3. SSH 密钥是否有效
4. Notion API 是否正常

配置完这些 Secrets 后，你的项目就能完整部署到 AWS 服务器了！🎉
