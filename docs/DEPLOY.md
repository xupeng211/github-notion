# CI/CD 部署说明（面向中国大陆、零基础）

本文仅使用 Gitee（最简单），镜像仓库推荐使用阿里云容器镜像服务（ACR）。

## 一、准备账号与信息

- Gitee 仓库：已开启 Gitee Go（工作流）
- 阿里云账号：开通“容器镜像服务 ACR（个人版/企业版均可）”
- 一台 Ubuntu EC2 服务器（可在 AWS 香港/新加坡等区，默认用户 ubuntu）

## 二、在阿里云 ACR 创建镜像仓库（含图示）

1) 进入 ACR 控制台 → 个人实例 或 企业实例（示意图）
   - 菜单路径：容器镜像服务 ACR → 实例 → 命名空间
   - 页面示例：
     ![实例与命名空间入口](./images/acr-namespace.png)
2) 选择地域（推荐：华东1-杭州）
   - 页面示例：
     ![地域选择示意](./images/acr-namespace.png)
3) 创建命名空间，比如 yourns（公开或私有均可）
   - 页面示例：
     ![创建命名空间示意](./images/acr-namespace.png)
4) 创建镜像仓库：名称 gitee-notion-sync，类型“私有”
   - 页面示例：
     ![创建仓库示意](./images/acr-repo.png)
5) 复制登录地址（示例）：registry.cn-hangzhou.aliyuncs.com
   - 页面示例：
     ![登录地址示意](./images/acr-login-endpoint.png)
6) 拼出 REGISTRY_HOST：registry.cn-hangzhou.aliyuncs.com/yourns/gitee-notion-sync
   - 说明示例：命名空间 yourns + 仓库名 gitee-notion-sync 组合
7) 在“访问凭证”页面创建 AK（用户名/密码）或使用账户密码
   - 页面示例：
     ![访问凭证示意](./images/acr-login-endpoint.png)

## 三、在 Gitee 配置 Secrets/变量

位置：仓库 → 管理 → Gitee Go → 环境变量/密钥

- 变量（可见）：
  - REGISTRY_HOST = registry.cn-hangzhou.aliyuncs.com/yourns/gitee-notion-sync
- 密钥（保密）：
  - REGISTRY_USER = 你的 ACR 用户名
  - REGISTRY_TOKEN = 你的 ACR 密码
  - EC2_HOST = 你的 EC2 公网 IP
  - EC2_SSH_USER = ubuntu（默认）
  - EC2_SSH_KEY = 粘贴你的私钥（PEM）
  - NOTION_TOKEN = 你的 Notion 集成 Token
  - GITEE_WEBHOOK_SECRET = 你自定义的密钥
  - GITEE_TOKEN = 你的 Gitee 私人令牌

保存后即可。

## 四、首次初始化 EC2（只做一次）

1) 本地终端登录：
   ssh -i <你的私钥> ubuntu@<EC2_HOST>

2) 运行初始化脚本（自动安装 Docker/Compose、开放端口、加固 SSH、设置时区）：
   sudo bash -lc 'bash -s' < infra/bootstrap_ec2.sh

3) 准备运行目录与环境文件：
   sudo mkdir -p /opt/gitee-notion-sync
   cd /opt/gitee-notion-sync
   sudo tee .env >/dev/null <<'EOF'
NOTION_TOKEN=替换为你的
NOTION_DATABASE_ID=替换为你的或留空
GITEE_WEBHOOK_SECRET=替换为你的
GITEE_TOKEN=替换为你的
SOURCE_OF_TRUTH=gitee
DB_URL=sqlite:///data/sync.db
APP_PORT=8000
LOG_LEVEL=INFO
EOF

提示：.env 存在于服务器本地，不要提交到仓库。

## 五、推送代码，自动部署

- 将代码推到 main 分支
- Gitee Go 会自动执行：
  1) 代码检查与测试
  2) 构建镜像并推送到 ACR（latest 和 提交哈希）
  3) 通过 SSH 登录 EC2，执行 infra/deploy.sh（滚动更新、健康检查）

部署成功后：
- 浏览器访问 http://<EC2_HOST>:8000/health 返回 200

## 死信重放与管理接口（生产验证）

- 环境变量：
  - DEADLETTER_REPLAY_TOKEN（建议设置为强随机字符串）
  - DEADLETTER_REPLAY_INTERVAL_MINUTES（默认 10 分钟，可按需调整）
- 在线验证：

```bash
curl -sS -X POST -H "Authorization: Bearer $DEADLETTER_REPLAY_TOKEN" https://$DOMAIN_NAME/replay-deadletters
curl -sS https://$DOMAIN_NAME/metrics | grep deadletter_replay_total
```

- 预期：
  - 第一个命令返回 {"replayed": N}
  - 第二个命令显示 deadletter_replay_total 指标，数值与重放次数相符


## 六、配置 Gitee Webhook（同步验证）

- 仓库 → 管理 → Webhook → 新增
- URL：http://<EC2_HOST>:8000/gitee_webhook
- 密钥：与 .env 中的 GITEE_WEBHOOK_SECRET 一致
- 触发事件：Issues（创建/编辑/关闭）+ Issue 评论
- 保存后点击“测试”，/health 与日志应显示事件已接收

## 七、回滚（失败时）

- 脚本会自动尝试回滚到上一个镜像
- 手工回滚（SSH 登录服务器）：
  cd /opt/gitee-notion-sync
  IMAGE_REF=${REGISTRY_HOST}:<previous_tag> ./infra/rollback.sh
