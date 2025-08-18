# 🚀 GitHub-Notion 同步服务部署清单

> **状态**: ✅ 所有架构问题已修复，可安全部署

## 📋 架构修复完成确认

### ✅ 已修复的关键问题

- [x] **数据库迁移冲突** - 移除 `init_db()` 调用，统一使用 Alembic
- [x] **环境变量命名不一致** - 统一使用 `DB_URL`
- [x] **同步/异步混合架构** - 添加异步版本函数
- [x] **错误处理机制** - 完善全局异常处理器
- [x] **核心功能实现** - 验证所有关键服务可用

### ✅ 新增功能和改进

- [x] **自动化启动脚本** - `scripts/start_service.py`
- [x] **数据库初始化脚本** - `scripts/init_db.py`
- [x] **架构验证脚本** - `scripts/validate_fixes.py`
- [x] **增强健康检查** - 包含 API 连接、磁盘空间、死信队列状态
- [x] **监控配置** - Prometheus + Grafana + 告警规则
- [x] **详细部署文档** - 涵盖多种部署方式

## 🔧 部署前验证

### 第一步：运行架构验证

```bash
python scripts/validate_fixes.py
```

**预期结果**:
```
🎉 所有测试通过！架构修复验证成功

📊 测试总结:
  总测试数: 9
  通过: 9
  失败: 0
  警告: 0
```

### 第二步：环境变量配置检查

```bash
# 复制并编辑环境变量
cp env.example .env

# 必需变量 (❌ 缺失会导致服务无法启动)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
NOTION_TOKEN=secret_xxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxx

# 推荐变量 (⚠️ 影响安全性和功能)
GITHUB_WEBHOOK_SECRET=your_secure_secret
NOTION_WEBHOOK_SECRET=your_secure_secret
DEADLETTER_REPLAY_TOKEN=your_admin_token

# 可选变量 (🔧 性能和运维优化)
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
RATE_LIMIT_PER_MINUTE=60
DB_URL=sqlite:///data/sync.db
```

### 第三步：依赖检查

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 验证关键依赖
python -c "import fastapi, uvicorn, httpx, alembic, prometheus_client; print('✅ 依赖检查通过')"
```

## 🚀 快速部署（推荐方式）

### 自动化部署

```bash
# 1. 配置环境变量
cp env.example .env
# 编辑 .env 文件

# 2. 使用自动化脚本启动
python scripts/start_service.py
```

**脚本会自动完成**:
- ✅ 环境变量验证
- ✅ 数据库初始化
- ✅ 服务健康检查
- ✅ 启动 FastAPI 服务

## 🏗️ 生产环境部署检查

### AWS EC2 部署

- [ ] **服务器配置**
  - [ ] Python 3.8+ 已安装
  - [ ] 磁盘空间 > 2GB
  - [ ] 网络访问 GitHub/Notion API
  - [ ] 防火墙开放端口 8000

- [ ] **环境配置**
  - [ ] 环境变量已设置到 `/etc/environment`
  - [ ] 系统服务文件已创建
  - [ ] 服务自启动已启用

- [ ] **安全配置**
  - [ ] 使用 HTTPS (Nginx/CloudFlare)
  - [ ] API tokens 安全存储
  - [ ] Webhook secrets 已配置

### Docker 部署

```bash
# 构建镜像
docker build -t github-notion-sync .

# 运行容器
docker run -d \
  --name github-notion-sync \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  github-notion-sync
```

- [ ] **容器配置**
  - [ ] 数据持久化卷已挂载
  - [ ] 环境变量已正确传递
  - [ ] 端口映射已配置
  - [ ] 健康检查已设置

## 🌐 Webhook 配置清单

### GitHub Webhook

- [ ] **仓库设置**
  - [ ] Webhook URL: `https://your-domain.com/github_webhook`
  - [ ] Content type: `application/json`
  - [ ] Secret: 与 `GITHUB_WEBHOOK_SECRET` 一致
  - [ ] Events: 选择 "Issues"
  - [ ] SSL verification: 启用

### Notion Integration

- [ ] **集成设置**
  - [ ] Integration 已创建
  - [ ] Token 已复制到环境变量
  - [ ] 数据库访问权限已授予
  - [ ] Database ID 已正确配置

## 🔍 部署后验证

### 服务状态检查

```bash
# 1. 健康检查
curl http://your-domain:8000/health

# 预期响应
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok"},
    "notion_api": {"status": "ok"},
    "github_api": {"status": "ok"},
    "disk_space": {"status": "ok"},
    "deadletter_queue": {"status": "ok"}
  }
}
```

### 功能测试

```bash
# 2. Prometheus 指标
curl http://your-domain:8000/metrics | grep events_total

# 3. 测试 GitHub Webhook
curl -X POST http://your-domain:8000/github_webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{"action": "opened", "issue": {"number": 1, "title": "Test"}}'

# 4. 死信队列管理
curl -X POST http://your-domain:8000/replay-deadletters \
  -H "Authorization: Bearer your-deadletter-token"
```

### 性能验证

- [ ] **响应时间**
  - [ ] `/health` 端点 < 500ms
  - [ ] Webhook 处理 < 2s
  - [ ] Notion API 调用 < 5s

- [ ] **错误率**
  - [ ] 事件处理成功率 > 95%
  - [ ] API 调用成功率 > 99%
  - [ ] 死信队列积压 < 10 条

## 📊 监控配置

### Prometheus 监控

```bash
# 部署 Prometheus
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### Grafana 仪表板

```bash
# 导入仪表板
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana-dashboard.json
```

### 告警配置

- [ ] **关键告警**
  - [ ] 服务离线告警
  - [ ] 高错误率告警
  - [ ] 死信队列积压告警
  - [ ] API 连接失败告警

- [ ] **资源告警**
  - [ ] 内存使用率 > 80%
  - [ ] 磁盘空间 < 10%
  - [ ] 处理延迟 > 5s

## 🚨 故障排除清单

### 常见问题诊断

| 问题症状 | 可能原因 | 解决方案 |
|---------|---------|----------|
| 服务启动失败 | 环境变量缺失 | 检查 `.env` 文件 |
| 数据库错误 | 迁移未执行 | 运行 `python scripts/init_db.py` |
| Notion API 403 | 权限不足 | 检查 Integration 数据库权限 |
| GitHub API 403 | Token 无效 | 重新生成 GitHub Token |
| Webhook 失败 | 签名验证失败 | 检查 webhook secret 配置 |

### 日志检查

```bash
# 系统服务日志
sudo journalctl -u github-notion-sync -f

# 应用日志
tail -f logs/app.log

# 错误模式匹配
grep -i "error\|fail\|exception" logs/app.log
```

## ✅ 最终部署确认

部署完成后，确认以下所有项目：

### 服务状态
- [ ] 服务正常运行
- [ ] 健康检查返回 "healthy"
- [ ] 所有 API 检查通过

### 功能验证
- [ ] GitHub webhook 接收正常
- [ ] Notion 页面创建成功
- [ ] 双向同步工作正常
- [ ] 死信队列处理正常

### 监控配置
- [ ] Prometheus 指标可访问
- [ ] Grafana 仪表板正常
- [ ] 告警规则已激活

### 安全配置
- [ ] 所有 secrets 已安全存储
- [ ] HTTPS 已启用
- [ ] 防火墙规则已配置

---

## 📞 技术支持

如果遇到问题：

1. **首先运行** `python scripts/validate_fixes.py`
2. **检查健康状态** `curl http://your-domain:8000/health`
3. **查看日志** `sudo journalctl -u github-notion-sync -f`
4. **验证环境变量** 确保所有必需变量已正确设置

**🎉 部署完成！您的 GitHub-Notion 同步服务已经可以稳定运行了。**
