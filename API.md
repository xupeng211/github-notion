# Gitee-Notion 同步服务 API 文档

## 概述

Gitee-Notion 同步服务提供了一套 Webhook API，用于实现 Gitee Issues 和 Notion 数据库之间的自动同步。

## 基础信息

- 基础 URL: `https://your-service-domain.com`
- API 版本: v1
- 内容类型: `application/json`

## 认证

所有 webhook 请求都需要进行签名验证：

- Gitee Webhook: 使用 `X-Gitee-Token` 头部
- Notion Webhook: 使用 `X-Notion-Signature` 头部

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
            {
                "name": "bug"
            }
        ],
        "created_at": "2024-02-20T10:00:00Z",
        "updated_at": "2024-02-20T10:00:00Z",
        "user": {
            "name": "example_user"
        }
    }
}
```

**响应：**
```json
{
    "status": "success",
    "message": "Webhook processed"
}
```

### 2. Notion Webhook 端点

#### POST /notion_webhook

（说明）当前 FastAPI 实现未启用该端点，保留为后续扩展项。

**请求头：**
```http
Content-Type: application/json
X-Notion-Signature: <webhook_signature>
```

**请求体示例（页面更新）：**
```json
{
    "type": "page_updated",
    "page": {
        "id": "page_id",
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": "更新的标题"
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "In Progress"
                }
            }
        }
    }
}
```

**响应：**
```json
{
    "status": "success",
    "message": "Page updated"
}
```

### 3. 健康检查端点

#### GET /health

检查服务的健康状态。

**响应示例：**
```json
{
    "status": "healthy",
    "timestamp": "2024-02-20T10:00:00Z",
    "environment": "production",
    "notion_api": {
        "connected": true,
        "version": "2022-06-28"
    },
    "app_info": {
        "app": "fastapi",
        "log_level": "INFO"
    }
}
```

### 4. 指标端点

#### GET /metrics

提供服务的 Prometheus 指标。

**响应格式：** Prometheus 文本格式

**示例指标：**
```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/gitee_webhook",status="200"} 100

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="POST",endpoint="/gitee_webhook",le="0.1"} 95
```

## 错误处理

服务使用标准的 HTTP 状态码表示请求的结果：

- 200: 请求成功
- 400: 请求格式错误
- 401: 认证失败
- 403: 权限不足
- 404: 资源不存在
- 429: 请求过于频繁
- 500: 服务器内部错误

错误响应格式：
```json
{
    "error": "error_code",
    "message": "详细错误信息",
    "timestamp": "2024-02-20T10:00:00Z"
}
```

## 速率限制

- Gitee Webhook: 5 请求/分钟
- Notion Webhook: 5 请求/分钟
- 其他端点: 200 请求/天，50 请求/小时

超过限制时返回 429 状态码。

## 最佳实践

1. **重试策略**
   - 建议在失败时实现指数退避重试
   - 最大重试次数：3次
   - 重试间隔：2秒、4秒、8秒

2. **错误处理**
   - 始终检查响应状态码
   - 记录详细的错误信息
   - 实现适当的错误恢复机制

3. **监控建议**
   - 监控 webhook 处理成功率
   - 跟踪响应时间
   - 设置适当的告警阈值

## 安全建议

1. **Webhook 安全**
   - 保护好 webhook 密钥
   - 始终验证请求签名
   - 使用 HTTPS 传输

2. **访问控制**
   - 实施 IP 白名单
   - 使用强密码策略
   - 定期轮换密钥

3. **数据安全**
   - 加密敏感数据
   - 实施数据备份
   - 遵守数据保留策略

## 示例代码

### Python 示例

```python
import requests
import hmac
import hashlib

def send_gitee_webhook(url, secret, payload):
    """发送 Gitee webhook 请求的示例"""
    headers = {
        'Content-Type': 'application/json',
        'X-Gitee-Token': hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# 使用示例
payload = {
    "action": "open",
    "issue": {
        "title": "测试 Issue",
        "body": "这是一个测试"
    }
}

result = send_gitee_webhook(
    "https://your-service.com/gitee_webhook",
    "your-webhook-secret",
    payload
)
print(result)
```

## 更新日志

### v1.0.0 (2024-02-20)
- 初始版本发布
- 支持基本的 Issue 同步功能
- 添加健康检查端点
- 实现基本的监控功能

## 支持

- 技术支持邮箱: support@example.com
- 文档更新日期: 2024-02-20 