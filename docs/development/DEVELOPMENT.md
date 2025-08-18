# 开发环境设置指南

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- Docker & Docker Compose
- Git
- Make

### 2. 一键设置开发环境
```bash
# 克隆项目
git clone <repository-url>
cd github-notion

# 设置开发环境
make setup-dev

# 验证环境
make quick-check
```

## 📋 开发工作流

### 标准开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/your-feature

# 2. 编写代码
# ... 编辑代码 ...

# 3. 自动修复代码问题
make fix

# 4. 运行完整检查
make check

# 5. 提交代码（会自动运行 pre-commit hooks）
git add .
git commit -m "feat: your feature description"

# 6. 推送代码
git push origin feature/your-feature
```

### 提交前必做检查
```bash
# 快速检查（推荐在每次 commit 前运行）
make quick-check

# 完整 CI 模拟（推荐在 PR 前运行）
make ci-local
```

## 🛠️ 可用命令

### 环境设置
```bash
make setup-dev      # 完整开发环境设置
make install-dev    # 仅安装开发依赖
```

### 代码质量
```bash
make format         # 格式化代码
make lint          # 代码质量检查
make fix           # 自动修复代码问题
make check         # 完整检查 (format + lint)
```

### 测试
```bash
make test          # 运行测试
make cov           # 运行测试并生成覆盖率报告
make test-prep     # 测试前准备
```

### 安全检查
```bash
make security      # 完整安全扫描
```

### Docker
```bash
make docker-build  # 构建 Docker 镜像
make docker-test   # 测试 Docker 镜像
```

### CI 模拟
```bash
make quick-check   # 快速检查（适合 commit 前）
make ci-local      # 完整本地 CI 模拟
make release-check # 发布前检查
```

### 清理
```bash
make clean         # 清理临时文件
```

## 🔧 工具配置

### 代码格式化
- **Black**: 代码格式化，行长度 120
- **isort**: 导入排序，兼容 Black
- **autoflake**: 移除未使用的导入和变量

### 代码质量检查
- **flake8**: 代码风格检查
- **mypy**: 类型检查（如果配置）

### 安全检查
- **detect-secrets**: 密钥泄露检测
- **bandit**: Python 代码安全扫描
- **safety**: 依赖安全检查

### 测试
- **pytest**: 测试框架
- **pytest-cov**: 覆盖率检查
- **pytest-xdist**: 并行测试

## 📁 项目结构

```
github-notion/
├── app/                    # 应用代码
├── tests/                  # 测试代码
├── scripts/                # 脚本文件
├── deploy/                 # 部署相关
├── .github/workflows/      # GitHub Actions
├── requirements.txt        # 生产依赖
├── requirements-dev.txt    # 开发依赖
├── Makefile               # 开发命令
├── .pre-commit-config.yaml # Git hooks 配置
├── pytest.ini            # 测试配置
└── DEVELOPMENT.md         # 本文档
```

## 🔍 故障排除

### 常见问题

#### 1. pre-commit hooks 失败
```bash
# 重新安装 hooks
pre-commit uninstall
pre-commit install

# 手动运行所有 hooks
pre-commit run --all-files
```

#### 2. 测试失败
```bash
# 查看详细测试输出
pytest tests/ -v --tb=long

# 运行特定测试
pytest tests/test_specific.py -v
```

#### 3. 格式检查失败
```bash
# 自动修复格式问题
make fix

# 检查具体的格式问题
black --check --diff .
isort --check-only --diff .
```

#### 4. 安全扫描误报
```bash
# 查看 detect-secrets 报告
cat detect-secrets-report.json

# 更新 secrets baseline
detect-secrets scan --update .secrets.baseline
```

### 环境重置
```bash
# 完全重置开发环境
make clean
rm -rf .venv/
python -m venv .venv
source .venv/bin/activate
make setup-dev
```

## 📊 CI/CD 流程

### GitHub Actions 工作流
1. **Policy Check**: 安全策略检查
2. **Code Quality**: 代码质量检查
3. **Security Scanning**: 安全扫描
4. **Testing**: 测试套件
5. **Build**: Docker 镜像构建
6. **Deploy**: 部署到生产环境

### 本地 CI 模拟
运行 `make ci-local` 会执行与 GitHub Actions 相同的检查流程，确保本地代码质量。

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 遵循开发工作流
4. 确保所有检查通过
5. 提交 Pull Request

## 📞 获取帮助

- 查看可用命令: `make help`
- 查看项目文档: `docs/`
- 提交 Issue: GitHub Issues
