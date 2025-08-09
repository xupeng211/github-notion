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


# 生产就绪的 Gitee ↔ Notion 同步服务



## 环境变量与本地启动

1) 复制环境模板并填写变量

- 生成 .env 草稿

```bash
make env
```

- 打开 .env 并填写必要值：
  - NOTION_TOKEN：前往 https://www.notion.so/my-integrations 创建 Integration，复制 Internal Integration Token
  - NOTION_DATABASE_ID：在浏览器打开你的数据库页面，Share -> Copy link，链接中类似 https://www.notion.so/xxxx?<db>=<DATABASE_ID>，或页面 URL 尾部的 32 字符 ID（去除连字符）
  - GITEE_TOKEN：登录 Gitee -> 设置 -> 私人令牌（Personal Access Token），生成并复制；至少勾选 repo、issues 权限
  - GITEE_WEBHOOK_SECRET：自定义一个强随机字符串；配置 Gitee Webhook 时保持一致
  - SOURCE_OF_TRUTH：gitee 或 notion，默认 gitee
  - DB_URL：例如 sqlite:///data/sync.db
  - APP_PORT：本地启动端口，例如 8000
  - LOG_LEVEL：INFO/DEBUG/WARN 等

2) 校验环境变量

```bash
make check-env
```

- 脚本会输出缺失项，并校验 DB_URL、APP_PORT 基本格式；失败返回码非 0。

3) 本地启动示例

- FastAPI 示例（app/server.py）：

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

- 结构化日志：启动后运行 scripts/dev_webhook.sh（从 .env 读取密钥）向服务发送签名事件，可在 docker compose logs -f app 中观察 JSON 日志。

## 如何验证幂等

- 同一 webhook 事件连续发送 3 次（scripts/dev_webhook.sh 可多次运行），应不重复创建 Notion 页面。我们基于事件内容哈希 + issue_id 去重，并对映射表（issue_id ↔ notion_page_id）进行 upsert，确保幂等。

## 生产 CI/CD 与部署

- 选择平台并配置 Secrets（见 docs/DEPLOY.md）
- 推送到 main 后：CI 构建镜像 → 推送 → SSH 到 EC2 执行部署脚本，完成滚动更新

### 配置 Gitee Webhook
- 仓库 → 管理 → Webhook → 新增
- URL：http://<EC2_HOST>:8000/gitee_webhook
- 密钥：使用 .env 的 GITEE_WEBHOOK_SECRET
- 触发事件：Issues（创建/编辑/关闭）+ Issue 评论
- 保存后点击“测试”，/health 与日志应显示事件已接收
