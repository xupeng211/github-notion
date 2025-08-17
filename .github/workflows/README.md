# 🚀 CI/CD Workflows 说明

## 📋 当前 Workflow 结构

### **🎯 主要 Workflows (推荐使用)**

| 文件名 | 用途 | 触发条件 | 状态 |
|--------|------|----------|------|
| `deploy.yml` | **生产部署** | `main` 分支推送 | ✅ 主要使用 |
| `ci.yml` | **持续集成** | PR 和分支推送 | ✅ 活跃 |
| `policy.yml` | **代码质量检查** | PR 和分支推送 | ✅ 活跃 |

### **🔧 辅助 Workflows**

| 文件名 | 用途 | 触发条件 | 状态 |
|--------|------|----------|------|
| `pr-check.yml` | **PR 检查** | Pull Request | ✅ 活跃 |
| `security-scan.yml` | **安全扫描** | 定时 + 手动 | ✅ 活跃 |
| `cd.yml` | **旧版部署** | 手动触发 | ⚠️ 已禁用 |

## 🎯 **推荐的 CI/CD 流程**

### **开发流程**
```
1. 创建功能分支
   ↓
2. 推送代码 → 触发 ci.yml (测试)
   ↓
3. 创建 PR → 触发 pr-check.yml (PR检查)
   ↓
4. 合并到 main → 触发 deploy.yml (部署)
```

### **部署流程 (deploy.yml)**
```
✅ 代码检出
✅ 检查必需的 Secrets
✅ 构建 Docker 镜像
✅ 推送到 GitHub Container Registry
✅ 部署到 AWS 服务器 (3.35.106.116)
✅ 健康检查
✅ 发送通知
```

## 🔐 **必需的 GitHub Secrets**

| Secret 名称 | 用途 | 必需程度 |
|------------|------|----------|
| `AWS_PRIVATE_KEY` | AWS EC2 SSH 私钥 | 🔴 必需 |
| `GITEE_WEBHOOK_SECRET` | Gitee webhook 密钥 | 🟡 推荐 |
| `GITHUB_WEBHOOK_SECRET` | GitHub webhook 密钥 | 🟡 推荐 |
| `NOTION_TOKEN` | Notion API 令牌 | 🟡 推荐 |
| `NOTION_DATABASE_ID` | Notion 数据库 ID | 🟡 推荐 |

详细配置说明请参考：[GITHUB_SECRETS_SETUP.md](../../GITHUB_SECRETS_SETUP.md)

## 🚨 **重要变更说明**

### **已禁用的 Workflows**
- `cd.yml` - 为避免与 `deploy.yml` 重复部署而禁用
- `main.yml`, `robust-ci.yml`, `simple-build.yml` - 已删除的重复文件

### **优化内容**
- ✅ 统一使用 `deploy.yml` 进行生产部署
- ✅ 简化 secrets 配置要求
- ✅ 增强 secrets 验证和错误提示
- ✅ 清理重复和过时的 workflow 文件

## 🎯 **使用建议**

### **日常开发**
- 使用 `ci.yml` 进行代码测试
- 使用 `pr-check.yml` 进行 PR 质量检查
- 使用 `policy.yml` 进行代码规范检查

### **生产部署**
- 只使用 `deploy.yml` 进行生产部署
- 确保所有必需的 secrets 已配置
- 监控部署日志确保成功

### **安全检查**
- `security-scan.yml` 定期运行安全扫描
- 及时处理发现的安全问题

## 📞 **故障排除**

### **部署失败**
1. 检查 GitHub Secrets 是否正确配置
2. 验证 AWS 服务器连接状态
3. 查看 deploy.yml 的详细日志

### **测试失败**
1. 本地运行测试确保通过
2. 检查环境依赖是否正确
3. 查看 ci.yml 的详细日志

### **安全扫描问题**
1. 检查是否有硬编码的敏感信息
2. 更新示例值避免误报
3. 查看 security-scan.yml 的详细日志

## 🔄 **维护建议**

1. **定期检查** workflow 运行状态
2. **及时更新** 依赖版本
3. **监控** 部署成功率
4. **优化** 构建和部署时间

这套优化后的 CI/CD 流程将为你提供稳定、高效的开发和部署体验！🚀
