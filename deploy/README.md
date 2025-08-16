# 部署入口（主线）

本目录为主部署目录，配合 GitHub Actions 的 cd.yml 完成自动发布。

## 主发布流
- main 分支 push → ci.yml（质量/测试/构建/冒烟）
- 通过后触发 cd.yml：
  1) 构建并推送镜像到 GHCR（latest、sha-<commit>）
  2) 预冒烟：在 Actions 侧启动 sha 镜像检查 /health
  3) 远端部署：SSH 到服务器，按 sha 镜像上线
  4) 健康检查：通过则晋级 stable；失败自动回滚 stable

## 先决条件
- 已在仓库 Settings → Secrets 配置：
  - PROD_HOST、PROD_USER、PROD_SSH_KEY
  - GITEE_WEBHOOK_SECRET、GITHUB_WEBHOOK_SECRET、DEADLETTER_REPLAY_TOKEN

## 手动演练（可选）
```bash
ssh $PROD_USER@$PROD_HOST
# 登录 GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
# 拉取并启动
docker pull ghcr.io/<org>/<repo>:sha-<commit>
IMAGE_TAG=ghcr.io/<org>/<repo>:sha-<commit> docker compose -f docker-compose.production.yml up -d
```

更多细节见 docs/CD_README.md。
