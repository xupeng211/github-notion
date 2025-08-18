# 🚀 开发指南

## 📋 开发文化

这个项目采用智能开发文化，注重自动化、质量和效率。

### 🛠️ 核心开发工具

#### 开发命令集 (`scripts/dev-commands.sh`)
提供智能开发命令：
- `smart_commit "消息"` - 智能提交（自动修复 + 提交）
- `safe_push` - 安全推送（诊断 + 推送）
- `dev_flow "消息"` - 完整流程（修复 + 提交 + 推送）
- `quick_fix` - 快速修复代码问题
- `local_test` - 本地构建测试

#### 硬编码检测工具 (`scripts/fix-hardcoded-values.py`)
自动检测和修复硬编码问题：
- IP 地址检测
- 端口号检测
- 文件路径检测
- 自动生成环境变量建议

#### 本地构建测试 (`scripts/test-build-locally.sh`)
本地验证构建过程：
- Docker 构建测试
- 容器启动验证
- 健康检查测试

### 🔄 开发流程

1. **开发阶段**
   ```bash
   # 加载开发命令
   source scripts/dev-commands.sh
   
   # 进行开发...
   
   # 智能提交
   smart_commit "feat: add new feature"
   ```

2. **测试阶段**
   ```bash
   # 本地构建测试
   ./scripts/test-build-locally.sh
   
   # 检查硬编码问题
   python3 scripts/fix-hardcoded-values.py
   ```

3. **部署阶段**
   ```bash
   # 安全推送
   safe_push
   ```

### 📚 文档结构

- `docs/BUILD_FIX_GUIDE.md` - 构建问题修复指南
- `docs/DEVELOPMENT_GUIDE.md` - 本文档
- `docs/DEPLOYMENT_GUIDE.md` - 部署指南（待创建）
- `docs/TROUBLESHOOTING.md` - 故障排除（待创建）

### 🎯 质量标准

- 自动代码格式化
- 硬编码检测
- 构建验证
- 健康检查
- 环境变量化配置

### 🚀 最佳实践

1. **使用智能命令**: 优先使用 `smart_commit` 和 `safe_push`
2. **本地验证**: 推送前使用 `local_test` 验证
3. **环境变量**: 使用 `.env.template` 管理配置
4. **文档更新**: 保持文档与代码同步
5. **质量检查**: 定期运行硬编码检测

## 🔧 工具使用

### 快速开始
```bash
# 1. 加载开发环境
source scripts/dev-commands.sh

# 2. 配置环境变量
cp .env.template .env
# 编辑 .env 文件

# 3. 本地测试
local_test

# 4. 开发流程
dev_flow "your commit message"
```

### 故障排除
如果遇到问题，请查看：
1. `docs/BUILD_FIX_GUIDE.md` - 构建问题
2. `docs/TROUBLESHOOTING.md` - 一般问题
3. 运行 `python3 scripts/fix-hardcoded-values.py` 检查配置

## 📞 支持

如果需要帮助，请：
1. 查看相关文档
2. 运行诊断工具
3. 检查日志文件
