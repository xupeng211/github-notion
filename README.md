# 项目说明
# 本地快速启动

- 生成并检查环境：

```bash
make env && make check-env
```

- 本地启动（单机）：

```bash
docker compose up -d
curl -sS http://localhost:8000/health
```

# 生产发布（Gitee + EC2 + ACR）

- 推送代码：

```bash
git push origin main
```

- 自动发布：Gitee Go → 构建镜像 → 推送 ACR → SSH 到 EC2 部署
- 验收：
  - 云上：curl -sS https://$DOMAIN_NAME/health
  - 重放死信（带鉴权）：

```bash
curl -sS -X POST -H "Authorization: Bearer $DEADLETTER_REPLAY_TOKEN" https://$DOMAIN_NAME/replay-deadletters
```

更多细节见 docs/DEPLOY.md
## 死信重放与管理接口

- 环境变量：
  - DEADLETTER_REPLAY_TOKEN（默认 changeme-secure-token，本地可直接使用）
  - DEADLETTER_REPLAY_INTERVAL_MINUTES（默认 10 分钟）
- 管理接口（需鉴权）：

```bash
curl -sS -X POST -H "Authorization: Bearer $DEADLETTER_REPLAY_TOKEN" http://localhost:8000/replay-deadletters
```

- 指标验证：

```bash
curl -sS http://localhost:8000/metrics | grep deadletter_replay_total
```



# 生产就绪的 GitHub ↔ Notion 双向同步服务（兼容 Gitee）



## 环境变量与本地启动

1) 复制环境模板并填写变量

- 生成 .env 草稿（依据 `.env.example`）

```bash
make env
```

- 打开 .env 并填写必要值：
  - NOTION_TOKEN：前往 https://www.notion.so/my-integrations 创建 Integration，复制 Internal Integration Token
  - NOTION_DATABASE_ID：在浏览器打开你的数据库页面，Share -> Copy link，链接中类似 https://www.notion.so/xxxx?<db>=<DATABASE_ID>，或页面 URL 尾部的 32 字符 ID（去除连字符）
  - NOTION_WEBHOOK_SECRET（可选）：若启用 Notion Webhook 自定义验签
  - GITEE_TOKEN（可选，兼容模式）：Gitee Personal Access Token
  - GITEE_WEBHOOK_SECRET（可选，兼容模式）：Gitee Webhook 密钥
  - GITHUB_TOKEN：GitHub Personal Access Token（需 repo / issues 权限）
  - GITHUB_WEBHOOK_SECRET：GitHub Webhook Secret（与 GitHub Webhook 配置一致）
  - DB_URL：例如 sqlite:///data/sync.db
  - APP_PORT：本地启动端口，例如 8000
  - LOG_LEVEL：INFO/DEBUG/WARN 等

2) 校验环境变量

```bash
make check-env
```

- 脚本会输出缺失项，并校验 DB_URL、APP_PORT 基本格式；失败返回码非 0。

3) 本地启动示例（FastAPI, app/server.py）

```bash
uvicorn app.server:app --port ${APP_PORT:-8000}
```

## 注意
- 不要提交 .env；已在 .gitignore 中忽略。
- 初次运行时 NOTION_DATABASE_ID 可留空，后续由初始化脚本写回。


## 本地快速启动

```bash
make env && make check-env && docker compose up -d && curl -sS :8000/health
```

- 结构化日志：启动后运行 `scripts/send_webhook.sh`（从 `.env` 读取密钥）向服务发送签名事件，可在 `docker compose logs -f app` 中观察 JSON 日志。

### 一键冒烟脚本

```bash
# 本机或容器（:8000）
bash scripts/run_smoke.sh --env-file ./.env --base-url http://127.0.0.1:8000

# 仅发一次 webhook（随机 issue id）
bash scripts/send_webhook.sh --env-file ./.env --url http://127.0.0.1:8000/gitee_webhook
```

## 健康检查响应示例

```json
{
  "status": "healthy",
  "timestamp": "2024-02-20T10:00:00Z",
  "environment": "development",
  "notion_api": {"connected": true, "version": "2022-06-28"},
  "app_info": {"app": "fastapi", "log_level": "INFO"}
}
```

## 开发与生产 Compose 说明
- 开发：`docker-compose.yml` 使用 `build: .`，注释 `image:` 字段。
- 生产：`docker-compose.prod.yml` 使用远端 `image:` 并挂载持久化卷。

## 可选速率限制
- 设置 `RATE_LIMIT_PER_MINUTE`（整数，默认 0 关闭）。
- 开启后，对 `/gitee_webhook`、`/github_webhook`、`/notion_webhook` 进行每分钟级全局限流，超额返回 429。

## Alembic 迁移
- 生成迁移：`alembic revision -m "change"`（或使用 `--autogenerate`，需比对元数据配置）
- 执行迁移：`alembic upgrade head`
- 回退一步：`alembic downgrade -1`
- 配置来源：`alembic.ini`（`sqlalchemy.url` 会从 `DB_URL` 环境变量读取）

## Nginx 限流示例（在 http{} 块）
```nginx
limit_req_zone $binary_remote_addr zone=rl_gitee:10m rate=5r/s;
server {
  location /gitee_webhook {
    limit_req zone=rl_gitee burst=10 nodelay;
    proxy_pass http://app:8000;
  }
  location /github_webhook {
    limit_req zone=rl_gitee burst=10 nodelay;
    proxy_pass http://app:8000;
  }
  location /notion_webhook {
    limit_req zone=rl_gitee burst=10 nodelay;
    proxy_pass http://app:8000;
  }
}
```

## 生产 CI/CD 与部署

- 选择平台并配置 Secrets（见 docs/DEPLOY.md）
- 推送到 main 后：CI 构建镜像 → 推送 → SSH 到 EC2 执行部署脚本，完成滚动更新

### 配置 Gitee Webhook（兼容）
- 仓库 → 管理 → Webhook → 新增
- URL：http://<EC2_HOST>:8000/gitee_webhook
- 密钥：使用 .env 的 GITEE_WEBHOOK_SECRET
- 触发事件：Issues（创建/编辑/关闭）+ Issue 评论
- 保存后点击“测试”，/health 与日志应显示事件已接收

### 配置 GitHub Webhook（双向同步）
- 仓库 → Settings → Webhooks → Add webhook
- Payload URL：`https://<DOMAIN>/github_webhook`
- Content type：`application/json`
- Secret：使用 `.env` 的 `GITHUB_WEBHOOK_SECRET`
- 选择事件：`Let me select individual events` → 勾选 `Issues`
- 保存后 GitHub 会发送 `ping`/`issues` 事件用于联通性验证
