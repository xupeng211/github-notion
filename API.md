# Gitee-Notion 同步服务 API 文档

## 概述

Gitee-Notion 同步服务提供了一套 Webhook API，用于实现 Gitee/GitHub Issues 与 Notion 数据库之间的自动同步（现已支持 GitHub ↔ Notion 双向）。

## 基础信息

- 基础 URL: `https://your-service-domain.com`
- API 版本: v1
- 内容类型: `application/json`

## 认证

所有 webhook 请求都需要进行签名验证：

- Gitee Webhook: 使用 `X-Gitee-Token` 头部（HMAC SHA256）
- GitHub Webhook: 使用 `X-Hub-Signature-256` 头部（HMAC SHA256）
- Notion Webhook: 使用 `X-Notion-Signature` 头部（可选，HMAC SHA256）

## API 端点

### 1. Gitee Webhook 端点

#### POST /gitee_webhook

接收来自 Gitee 的 webhook 事件，处理 Issue 相关操作。

**请求头：**
```http
Content-Type: application/json
X-Gitee-Token: <webhook_secret>
X-Gitee-Event: Issue Hook
```

**请求体示例（Issue 创建）：**
```json
{
    "action": "open",
    "issue": {
        "number": "123",
        "title": "示例 Issue",
        "body": "这是一个示例 Issue 的内容",
        "state": "open",
        "labels": [
            { "name": "bug" }
        ],
        "created_at": "2024-02-20T10:00:00Z",
        "updated_at": "2024-02-20T10:00:00Z",
        "user": { "name": "example_user" }
    }
}
```

**响应：**
```json
{ "message": "ok" }
```

### 2. GitHub Webhook 端点

#### POST /github_webhook

接收来自 GitHub 的 `issues` 事件，与 Notion 同步（创建/更新页面）。

**请求头：**
```http
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
X-GitHub-Event: issues
```

**请求体字段（节选）：**
```json
{
  "action": "opened|edited|closed|reopened",
  "issue": {
    "number": 42,
    "title": "Bug: cannot save",
    "body": "...",
    "state": "open|closed",
    "html_url": "https://github.com/org/repo/issues/42"
  },
  "repository": { "name": "repo", "owner": {"login": "org"} }
}
```

**响应：**
```json
{ "message": "ok" }
```

### 3. Notion Webhook 端点

#### POST /notion_webhook

接收来自 Notion 的页面变更（page_updated 等），与 GitHub Issue 回写同步。

**请求头：**
```http
Content-Type: application/json
X-Notion-Signature: sha256=<signature>  # 可选，若配置 NOTION_WEBHOOK_SECRET
```

**请求体示例（页面更新）：**
```json
{
    "type": "page_updated",
    "page": {
        "id": "page_id",
        "properties": {
      "Task": { "title": [{ "text": { "content": "更新的标题" } }] },
      "Status": { "select": { "name": "In Progress" } },
      "Output": { "rich_text": [{ "text": { "content": "正文" } }] }
        }
    }
}
```

**响应：**
```json
{ "message": "ok" }
```

### 4. 健康检查端点

#### GET /health

检查服务的健康状态。

**响应示例：**
```json
{
    "status": "healthy",
    "timestamp": "2024-02-20T10:00:00Z",
    "environment": "production",
  "notion_api": { "connected": true, "version": "2022-06-28" },
  "app_info": { "app": "fastapi", "log_level": "INFO" }
}
```

### 5. 指标端点

#### GET /metrics

提供服务的 Prometheus 指标。

**响应格式：** Prometheus 文本格式

## 错误处理

服务使用标准的 HTTP 状态码表示请求的结果：

- 200: 请求成功
- 400: 请求格式错误
- 401: 认证失败
- 403: 权限不足
- 404: 资源不存在
- 429: 请求过于频繁
- 500: 服务器内部错误

**错误响应格式：**
```json
{ "error": "error_code", "message": "详细错误信息", "timestamp": "2024-02-20T10:00:00Z" }
```

## 速率限制

- `/gitee_webhook`, `/github_webhook`, `/notion_webhook`: 按 `RATE_LIMIT_PER_MINUTE` 全局限流

## 最佳实践

1. 重试策略：指数退避、最大 3-5 次
2. 错误处理：记录详细信息并入死信
3. 监控建议：成功率与时延，设置告警

## 安全建议

1. Webhook 安全：保护密钥、验证签名、HTTPS
2. 访问控制：IP 白名单、强密码、密钥轮换
3. 数据安全：加密、备份、保留策略

## 示例代码

略（参考 `scripts/send_webhook.sh` 并自定义 GitHub 版本）

## 更新日志

- v1.1.0: 新增 GitHub ↔ Notion 双向同步、启用 `/github_webhook`、`/notion_webhook`
- v1.0.0: 初始版本 