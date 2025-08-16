# 生产环境部署（15 分钟）

目标：将 main 分支代码以容器形式部署到你的服务器，并具备“失败自动回滚”。

## 先决条件
- 一台 Linux 服务器（Ubuntu 20.04+/Debian/CentOS 均可）
- 已配置 GitHub Actions Secrets：
  - PROD_HOST、PROD_USER、PROD_SSH_KEY
  - GITEE_WEBHOOK_SECRET、GITHUB_WEBHOOK_SECRET、DEADLETTER_REPLAY_TOKEN
  - 可选：NOTION_TOKEN、NOTION_DATABASE_ID

## 流程总览
1. 推送到 main → 触发 CI（测试/质量/覆盖率）
2. 触发 CD（构建并推送 GHCR 镜像：latest、sha-<commit>）
3. 预冒烟：在 Actions 侧拉起 sha- 镜像验证 /health
4. 部署到服务器：按 sha-<commit> 镜像上线
5. 健康检查：/health 通过则晋级 stable；失败则回滚 stable

## 服务器准备
无需预装 Docker/Compose，CD 会自动安装（如缺失）。建议预留：
- 开放端口：8000（或你的服务端口）
- 磁盘空间：2~4 GB（镜像缓存）

## 手动部署（可选）
如果你希望先手动演练：
```bash
ssh $PROD_USER@$PROD_HOST
# 登录 GHCR
echo <TOKEN> | docker login ghcr.io -u <USER> --password-stdin
# 拉取镜像并启动
docker pull ghcr.io/<org>/<repo>:sha-<commit>
docker run -d -p 8000:8000 \
  -e GITEE_WEBHOOK_SECRET=prod \
  -e GITHUB_WEBHOOK_SECRET=prod \
  -e DEADLETTER_REPLAY_TOKEN=prod \
  ghcr.io/<org>/<repo>:sha-<commit>
```

## 回滚策略
- 控制台回滚：将正在运行的镜像切换回 ghcr.io/<org>/<repo>:stable
- CD 会在健康检查失败时自动回滚并再次校验

## 进一步加固
- 开启 GitHub 环境保护（production 需要审批）
- 将 policy.yml 的 secret 扫描规则加严
- 在 Compose 挂载数据卷与只读根文件系统
