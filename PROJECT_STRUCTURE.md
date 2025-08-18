# 🏗️ 项目结构

## 📁 核心目录结构

```
github-notion/
├── 📱 app/                    # 应用核心代码
│   ├── server.py              # FastAPI 服务器
│   ├── models.py              # 数据模型
│   ├── service.py             # 业务逻辑
│   └── ...                    # 其他应用文件
├── 🧪 tests/                  # 测试文件
├── 📚 docs/                   # 项目文档
│   ├── README.md              # 文档索引
│   ├── DEVELOPMENT_GUIDE.md   # 开发指南
│   ├── BUILD_FIX_GUIDE.md     # 构建修复指南
│   ├── DEPLOYMENT_GUIDE.md    # 部署指南
│   ├── guides/                # 操作指南 (26个文档)
│   ├── deployment/            # 部署文档 (11个文档)
│   ├── development/           # 开发文档 (7个文档)
│   └── troubleshooting/       # 故障排除 (6个文档)
├── 🛠️ scripts/               # 开发脚本
│   ├── README.md              # 脚本说明
│   ├── dev-commands.sh        # 智能开发命令
│   ├── fix-hardcoded-values.py # 硬编码检测
│   ├── test-build-locally.sh  # 本地构建测试
│   └── ...                    # 其他开发脚本
├── 🔧 .github/workflows/      # CI/CD 工作流
│   ├── ci-build.yml           # 主要 CI/CD 流程
│   └── optimized-build.yml    # 优化构建流程 (手动触发)
├── 🐳 Docker 配置
│   ├── Dockerfile             # 标准 Docker 配置
│   ├── Dockerfile.github      # GitHub Actions 专用
│   └── docker-compose.yml     # Docker Compose 配置
├── 📋 配置文件
│   ├── requirements.txt       # Python 依赖
│   ├── .env.template          # 环境变量模板
│   ├── .gitignore             # Git 忽略文件
│   └── pyproject.toml         # Python 项目配置
└── 📖 README.md               # 项目说明
```

## 🎯 核心特性

### 🚀 智能开发文化
- **智能命令**: `source scripts/dev-commands.sh`
- **自动修复**: `smart_commit "消息"`
- **安全推送**: `safe_push`
- **完整流程**: `dev_flow "消息"`
- **本地测试**: `local_test`
- **快速修复**: `quick_fix`

### 🔧 开发工具
- **硬编码检测**: `python3 scripts/fix-hardcoded-values.py`
- **构建测试**: `./scripts/test-build-locally.sh`
- **代码质量**: 自动格式化和检查
- **环境变量**: `.env.template` 模板

### 📚 完整文档体系
- **开发指南**: `docs/DEVELOPMENT_GUIDE.md`
- **构建修复**: `docs/BUILD_FIX_GUIDE.md`
- **部署指南**: `docs/DEPLOYMENT_GUIDE.md`
- **故障排除**: `docs/troubleshooting/`
- **操作指南**: `docs/guides/`

### 🐳 容器化部署
- **本地开发**: `docker-compose up -d`
- **生产部署**: GitHub Actions 自动化
- **健康检查**: `/health` 和 `/health/ci` 端点
- **智能构建**: 环境感知的健康检查

## 🔄 开发流程

### 1. 环境设置
```bash
# 克隆项目
git clone <repository>
cd github-notion

# 配置环境
cp .env.template .env
# 编辑 .env 文件

# 加载开发命令
source scripts/dev-commands.sh
```

### 2. 智能开发工作流
```bash
# 开发代码...

# 智能提交（自动修复 + 提交）
smart_commit "feat: add new feature"

# 安全推送（诊断 + 推送）
safe_push

# 或者完整流程
dev_flow "fix: resolve issue"
```

### 3. 测试和验证
```bash
# 本地构建测试
local_test

# 硬编码检测
python3 scripts/fix-hardcoded-values.py

# 快速修复
quick_fix

# 运行测试
pytest tests/
```

## 📞 获取帮助

1. **查看文档**: `docs/README.md`
2. **开发指南**: `docs/DEVELOPMENT_GUIDE.md`
3. **故障排除**: `docs/troubleshooting/`
4. **脚本帮助**: `scripts/README.md`

## 🎉 项目亮点

- ✅ **智能开发文化**: 自动化优先，质量保证
- ✅ **完整文档体系**: 50+ 文档，从开发到部署的全流程指南
- ✅ **强大的工具链**: 硬编码检测、构建测试、自动修复
- ✅ **容器化部署**: Docker + GitHub Actions 自动化
- ✅ **健康检查**: 完善的监控和诊断机制
- ✅ **工作流优化**: 消除冲突，确保构建成功

## 🚀 开发文化核心

### 智能命令系统
```bash
source scripts/dev-commands.sh

# 可用命令:
smart_commit "消息"  # 智能提交（自动修复 + 提交）
safe_push           # 安全推送（诊断 + 推送）
dev_flow "消息"     # 完整流程（修复 + 提交 + 推送）
quick_fix           # 快速修复代码问题
local_test          # 本地构建测试
```

### 质量保证机制
- 自动代码格式化
- 硬编码检测和修复
- 构建前验证
- 健康检查验证
- 环境变量化配置

### 文档驱动开发
- 完整的文档索引
- 分类清晰的指南
- 故障排除手册
- 最佳实践指导

这个项目结构体现了现代软件开发的最佳实践，将开发文化、工具链和文档有机结合，为开发者提供了高效、可靠的开发体验。
