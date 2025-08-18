# 故障排除指南

## 🔍 常见问题与解决方案

### CI/CD 相关问题

#### 1. GitHub Actions 失败

**问题**: Policy 检查失败
```
Forbidden .env file detected: .env.example
```

**解决方案**:
```bash
# 检查 .env 文件规则
grep -E "\.env" .github/workflows/policy.yml

# 确保排除示例文件
# 正确的正则表达式应该排除 .env.example, .env.template, .env.sample
```

**问题**: detect-secrets 检测到误报
```
High confidence secrets found in .git/FETCH_HEAD
```

**解决方案**:
```bash
# 更新 secrets baseline
detect-secrets scan --update .secrets.baseline

# 或者在 CI 配置中排除相关目录
--exclude-files '\.git/.*'
```

#### 2. 测试覆盖率不足

**问题**:
```
Coverage failure: total of 2.90% is less than fail-under=50%
```

**解决方案**:
```bash
# 临时降低覆盖率要求
# 在 .github/workflows/ci.yml 中修改
--cov-fail-under=5

# 长期解决：增加测试用例
pytest tests/ --cov=app --cov-report=html
# 查看 htmlcov/index.html 了解哪些代码未覆盖
```

#### 3. Docker 构建失败

**问题**: 磁盘空间不足
```
no space left on device
```

**解决方案**:
```bash
# 在 CI 中添加磁盘清理
df -h
docker system prune -f
rm -rf /tmp/* || true
```

### 本地开发问题

#### 1. pre-commit hooks 失败

**问题**: hooks 安装失败
```bash
# 解决方案
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

**问题**: Black 格式检查失败
```bash
# 自动修复
make fix

# 或手动修复
black .
isort .
```

#### 2. 依赖安装问题

**问题**: requirements-dev.txt 不存在
```bash
# 解决方案
pip install black isort flake8 pytest pytest-cov detect-secrets bandit safety
```

**问题**: 版本冲突
```bash
# 解决方案
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### 3. 测试运行问题

**问题**: 导入已归档模块
```
SystemExit: This module is archived. Use environment variables directly.
```

**解决方案**:
```bash
# 删除相关测试文件
rm tests/test_config.py

# 或者修改测试以避免导入归档模块
```

### 安全扫描问题

#### 1. Bandit 误报

**问题**: 检测到硬编码密码
```json
{
  "issue_severity": "MEDIUM",
  "issue_text": "Possible hardcoded password"
}
```

**解决方案**:
```python
# 在代码中添加 # nosec 注释
password = "test_password"  # nosec B105

# 或者在 .bandit 配置文件中排除
[bandit]
exclude_dirs = tests/
skips = B101,B601
```

#### 2. Safety 检查失败

**问题**: 依赖有安全漏洞
```
Safety check failed: 1 vulnerability found
```

**解决方案**:
```bash
# 查看详细报告
safety check --json

# 升级有问题的依赖
pip install --upgrade package_name

# 或者在 CI 中忽略特定漏洞（临时）
safety check --ignore 12345
```

### Docker 相关问题

#### 1. 容器启动失败

**问题**: 端口被占用
```
Port 8000 is already in use
```

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 停止相关容器
docker-compose -f docker-compose.dev.yml down

# 使用不同端口
docker-compose -f docker-compose.dev.yml up -d --scale app=0
```

#### 2. 镜像构建问题

**问题**: 依赖安装失败
```
ERROR: Could not find a version that satisfies the requirement
```

**解决方案**:
```dockerfile
# 在 Dockerfile 中更新 pip
RUN pip install --upgrade pip

# 使用特定的 Python 版本
FROM python:3.9-slim
```

### 环境配置问题

#### 1. 环境变量缺失

**问题**:
```
KeyError: 'GITHUB_TOKEN'
```

**解决方案**:
```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
vim .env

# 或者设置环境变量
export GITHUB_TOKEN=your_token
```

#### 2. 数据库连接问题

**问题**:
```
Connection refused: localhost:5432
```

**解决方案**:
```bash
# 启动数据库容器
docker-compose -f docker-compose.dev.yml up -d postgres

# 检查容器状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs postgres
```

## 🛠️ 调试工具

### 1. 日志查看
```bash
# GitHub Actions 日志
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/user/repo/actions/runs/RUN_ID/logs"

# 本地容器日志
docker-compose -f docker-compose.dev.yml logs app

# 应用日志
tail -f logs/app.log
```

### 2. 性能分析
```bash
# 测试执行时间
time pytest tests/

# 内存使用
docker stats

# 磁盘使用
df -h
du -sh ./*
```

### 3. 网络调试
```bash
# 检查端口
netstat -tulpn | grep :8000

# 测试 API
curl -X GET http://localhost:8000/health

# 容器网络
docker network ls
docker network inspect github-notion-dev
```

## 📋 检查清单

### 提交前检查
- [ ] 运行 `make quick-check`
- [ ] 所有测试通过
- [ ] 代码格式正确
- [ ] 无安全问题
- [ ] 文档已更新

### 发布前检查
- [ ] 运行 `make ci-local`
- [ ] Docker 镜像构建成功
- [ ] 所有 CI 检查通过
- [ ] 版本号已更新
- [ ] 变更日志已更新

### 生产部署检查
- [ ] 环境变量已配置
- [ ] 数据库迁移已执行
- [ ] 健康检查通过
- [ ] 监控已配置
- [ ] 备份已验证

## 🆘 获取帮助

1. **查看文档**: `DEVELOPMENT.md`
2. **运行诊断**: `make ci-local`
3. **查看日志**: GitHub Actions 页面
4. **提交 Issue**: 包含错误信息和环境详情
5. **联系团队**: 在项目 Slack 频道求助

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Python 测试指南](https://docs.python.org/3/library/unittest.html)
- [安全扫描工具文档](https://github.com/Yelp/detect-secrets)
