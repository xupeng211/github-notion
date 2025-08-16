# 部署常见问题（FAQ）

## 1. 发布成功但服务不健康，如何排查？
- 查看 Actions 日志中“Pre-deploy Smoke”和“健康检查”步骤的失败原因
- SSH 到服务器：`docker compose -f docker-compose.production.yml ps && docker compose -f docker-compose.production.yml logs --tail 200`
- 常见原因：环境变量缺失/占位值、端口占用、数据库连通性

## 2. 如何手动回滚？
- 将镜像切回 stable：
```bash
IMAGE_TAG=ghcr.io/<org>/<repo>:stable docker compose -f docker-compose.production.yml up -d
```
- 验证健康：`curl -fsS http://127.0.0.1:8000/health`

## 3. 线上用的是什么镜像？
- 服务器上执行：`docker compose -f docker-compose.production.yml images`
- 或：`docker ps --format '{{.Image}} {{.Names}}'`

## 4. 如何仅重启应用容器？
```bash
docker compose -f docker-compose.production.yml restart app
```

## 5. 如何更新环境变量？
- 修改服务器上的 `.env`
- 重新 `docker compose -f docker-compose.production.yml up -d`

## 6. GHCR 拉取失败（401/403）？
- 检查服务器 `docker login ghcr.io` 是否使用有效的 token
- 网络限制场景下考虑配置代理或使用镜像加速

更多请参考 docs/CD_README.md。
