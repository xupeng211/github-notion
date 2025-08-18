# 🔐 GitHub Secrets 管理指南

本指南介绍如何使用项目提供的工具来管理 GitHub Secrets，确保 CI/CD 流程正常运行。

## 📋 **工具概览**

| 工具 | 用途 | 文件路径 |
|------|------|----------|
| **配置工具** | 批量设置 GitHub Secrets | `tools/configure_secrets.sh` |
| **校验工具** | 验证 Secrets 配置完整性 | `tools/validate_workflows.py` |
| **清理工具** | 删除废弃/未使用的 Secrets | `tools/cleanup_secrets.sh` |

## 🎯 **快速开始**

### **1. 检查当前状态**

```bash
# 校验当前 secrets 配置
python3 tools/validate_workflows.py

# 查看详细信息
python3 tools/validate_workflows.py --verbose
```

### **2. 配置缺失的 Secrets**

```bash
# 使用配置工具（推荐）
./tools/configure_secrets.sh

# 或者手动配置
gh secret set SECRET_NAME --repo owner/repo
```

### **3. 清理废弃的 Secrets**

```bash
# 预览将要删除的 secrets（安全）
./tools/cleanup_secrets.sh

# 执行实际删除
./tools/cleanup_secrets.sh --execute
```

## 🔑 **必需的 Secrets 清单**

### **🔴 必需配置（4个）**

| Secret 名称 | 用途 | 获取方式 | 最小权限 |
|-------------|------|----------|----------|
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook 签名验证 | 自定义生成 | 无（密钥字符串） |
| `NOTION_TOKEN` | Notion API 访问 | Notion Integrations | 读写目标数据库 |
| `NOTION_DATABASE_ID` | Notion 目标数据库 | Notion 数据库 URL | 无（数据库 ID） |
| `AWS_PRIVATE_KEY` | EC2 SSH 访问 | AWS EC2 密钥对 | EC2 实例访问 |

### **🟡 推荐配置（2个）**

| Secret 名称 | 用途 | 获取方式 | 最小权限 |
|-------------|------|----------|----------|
| `GITHUB_TOKEN` | GitHub API 访问 | GitHub PAT | `repo`, `admin:repo_hook` |
| `DEADLETTER_REPLAY_TOKEN` | 死信队列管理 | 自定义生成 | 无（管理令牌） |

## 🛠️ **详细使用说明**

### **配置工具 (`configure_secrets.sh`)**

#### **基本用法**

```bash
# 使用默认配置文件
./tools/configure_secrets.sh

# 指定自定义配置文件
./tools/configure_secrets.sh -f my-secrets.env

# 指定目标仓库
./tools/configure_secrets.sh -r myorg/myrepo
```

#### **配置文件格式 (`.secrets.env`)**

```bash
# GitHub Secrets 配置文件
# 注意：此文件包含敏感信息，不要提交到版本控制

# 必需配置
GITHUB_WEBHOOK_SECRET=your_secure_webhook_secret_32chars_minimum
NOTION_TOKEN=secret_your_notion_integration_token_here
NOTION_DATABASE_ID=your-notion-database-id-here
AWS_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...your private key content...
-----END RSA PRIVATE KEY-----"

# 推荐配置
GITHUB_TOKEN=ghp_your_github_personal_access_token_here
DEADLETTER_REPLAY_TOKEN=your_secure_deadletter_token_32chars
```

#### **交互式配置**

如果没有配置文件，工具会提示交互式输入：

```bash
$ ./tools/configure_secrets.sh

🔐 GitHub Secrets 批量配置工具
=================================

配置 GITHUB_WEBHOOK_SECRET
描述: GitHub webhook 签名验证密钥
优先级: 必需

请输入 GITHUB_WEBHOOK_SECRET: [隐藏输入]
```

### **校验工具 (`validate_workflows.py`)**

#### **基本用法**

```bash
# 基本校验
python3 tools/validate_workflows.py

# 详细模式
python3 tools/validate_workflows.py --verbose

# JSON 输出（用于脚本集成）
python3 tools/validate_workflows.py --json
```

#### **输出示例**

```
🔍 GitHub Workflows Secrets 校验工具
==================================================

ℹ️  扫描 workflow 文件...
ℹ️  获取当前仓库 secrets...
ℹ️  分析差异...

📊 差异分析结果:

❌ 缺失的必需 Secrets (2):
  - GITHUB_WEBHOOK_SECRET: GitHub webhook 签名验证密钥
  - NOTION_TOKEN: Notion API 访问令牌

⚠️  缺失的推荐 Secrets (1):
  - GITHUB_TOKEN: GitHub API 访问令牌

🗑️  废弃的 Secrets (1):
  - GITEE_WEBHOOK_SECRET: Gitee 功能已移除

📈 统计总结:
  Workflow 中的 Secrets: 5
  当前已配置的 Secrets: 3
  缺失的 Secrets: 3
  多余/废弃的 Secrets: 1
```

### **清理工具 (`cleanup_secrets.sh`)**

#### **安全清理流程**

```bash
# 1. 预览模式（推荐先运行）
./tools/cleanup_secrets.sh

# 2. 确认无误后执行删除
./tools/cleanup_secrets.sh --execute

# 3. 强制删除（跳过确认）
./tools/cleanup_secrets.sh --execute --force
```

#### **选项说明**

| 选项 | 说明 | 安全性 |
|------|------|--------|
| `--dry-run` | 模拟运行（默认） | ✅ 安全 |
| `--execute` | 执行实际删除 | ⚠️ 不可逆 |
| `--force` | 跳过确认提示 | ❌ 危险 |
| `--yes` | 非交互模式 | ⚠️ 自动化 |

## 🔒 **安全最佳实践**

### **1. Secrets 生成**

```bash
# 生成安全的 webhook secret（32字符）
openssl rand -hex 32

# 生成更长的密钥（64字符）
openssl rand -hex 64

# 生成 base64 编码的密钥
openssl rand -base64 32
```

### **2. 权限最小化**

#### **GitHub Token 权限**

创建 GitHub Personal Access Token 时，只授予必要权限：

- ✅ `repo` - 仓库访问
- ✅ `admin:repo_hook` - webhook 管理
- ❌ `admin:org` - 不需要组织管理权限
- ❌ `user` - 不需要用户信息权限

#### **Notion Integration 权限**

配置 Notion Integration 时：

- ✅ 只连接目标数据库
- ✅ 授予读写权限
- ❌ 不要授予整个工作区权限

### **3. 定期轮换**

建议定期更新以下 secrets：

| Secret | 轮换频率 | 原因 |
|--------|----------|------|
| `GITHUB_WEBHOOK_SECRET` | 6个月 | 防止密钥泄露 |
| `GITHUB_TOKEN` | 3个月 | 限制令牌生命周期 |
| `NOTION_TOKEN` | 6个月 | API 安全最佳实践 |
| `AWS_PRIVATE_KEY` | 1年 | SSH 密钥安全 |

### **4. 监控和审计**

```bash
# 定期检查 secrets 状态
python3 tools/validate_workflows.py

# 查看 secrets 使用情况
gh secret list --repo owner/repo

# 检查最近的 workflow 运行
gh run list --repo owner/repo
```

## 🚨 **故障排除**

### **常见问题**

#### **1. GitHub CLI 未登录**

```bash
错误: GitHub CLI 未登录
解决: gh auth login
```

#### **2. 权限不足**

```bash
错误: HTTP 403: Resource not accessible by integration
解决: 检查 GitHub Token 权限，确保包含 repo 和 admin:repo_hook
```

#### **3. PEM 密钥格式错误**

```bash
错误: PEM 私钥格式无效
解决: 确保包含完整的 -----BEGIN PRIVATE KEY----- 和 -----END PRIVATE KEY----- 行
```

#### **4. Notion API 错误**

```bash
错误: Notion API 调用失败
解决:
1. 检查 NOTION_TOKEN 是否正确
2. 确认 Integration 已连接到目标数据库
3. 验证 NOTION_DATABASE_ID 格式正确
```

### **调试命令**

```bash
# 检查 GitHub CLI 状态
gh auth status

# 测试仓库访问
gh repo view owner/repo

# 验证 secrets 列表
gh secret list --repo owner/repo

# 检查 workflow 文件语法
yamllint .github/workflows/*.yml
```

## 📚 **参考资料**

- [GitHub CLI 文档](https://cli.github.com/manual/)
- [GitHub Secrets 文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Notion API 文档](https://developers.notion.com/)
- [AWS EC2 密钥对文档](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)

## 🆘 **获取帮助**

如果遇到问题，可以：

1. 查看工具的帮助信息：`./tools/configure_secrets.sh --help`
2. 运行校验工具诊断：`python3 tools/validate_workflows.py --verbose`
3. 检查 GitHub Actions 运行日志
4. 查阅项目文档和 issue

---

**⚠️ 重要提醒：Secrets 包含敏感信息，请妥善保管，不要在公开场所分享或提交到版本控制系统。**
