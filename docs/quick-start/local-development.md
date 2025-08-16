# 本地开发环境搭建（5 分钟）

本文帮助你在本地拉起服务、跑通单测与基础质量检查。

## 前置条件
- Python 3.11+
- Git、Make、curl
- 可选：Docker（用于容器化验证）

## 克隆与安装
```bash
git clone <your-repo-url>
cd <repo>
python -m venv .venv && source .venv/bin/activate   # 可选
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install && pre-commit install --hook-type commit-msg --hook-type pre-push
```

## 运行质量检查
```bash
# 代码格式与静态检查
ruff check .
ruff format . --check
mypy . || true          # 初期宽松

# 单元测试与覆盖率
pytest -q
coverage run -m pytest -q && coverage report -m
```

## 启动应用（二选一）

方式 A：使用 Uvicorn 直接启动
```bash
# 常见入口（若有变动，以仓库实际为准）
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
# 健康检查
curl -fsS http://127.0.0.1:8000/health
```

方式 B：使用 Docker 本地运行
```bash
# 构建镜像
docker build -t local/app:dev -f Dockerfile .
# 以最小必需环境变量运行（示例值请替换）
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=local \
  -e LOG_LEVEL=INFO \
  -e GITEE_WEBHOOK_SECRET=dev-secret \
  -e GITHUB_WEBHOOK_SECRET=dev-secret \
  -e DEADLETTER_REPLAY_TOKEN=dev-secret \
  -e DB_URL=sqlite:///data/sync.db \
  local/app:dev
```

## 常见问题
- 启动即退出，日志提示缺失密钥：请按日志提示设置 GITEE_WEBHOOK_SECRET / GITHUB_WEBHOOK_SECRET / DEADLETTER_REPLAY_TOKEN
- 覆盖率报告阈值：初期阈值较宽（60），可逐步提高

## 下一步
- 阅读 docs/CD_README.md 了解 CI/CD 与合并策略
- 阅读 quick-start/production-deployment.md 开始部署
