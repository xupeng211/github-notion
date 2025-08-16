# Docker 容器部署（10 分钟）

适合本地或单机快速部署与验证。

## 构建镜像
```bash
docker build -t my/app:latest -f Dockerfile .
```

## 运行容器（最小必需变量）
```bash
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=INFO \
  -e GITEE_WEBHOOK_SECRET=secret \
  -e GITHUB_WEBHOOK_SECRET=secret \
  -e DEADLETTER_REPLAY_TOKEN=secret \
  -e DB_URL=sqlite:///data/sync.db \
  my/app:latest
```

## 健康检查
```bash
curl -fsS http://127.0.0.1:8000/health
```

## 常见问题
- 容器立即退出：检查必需环境变量是否缺失或使用占位值
- 端口冲突：调整 -p 8000:8000 左侧主机端口
