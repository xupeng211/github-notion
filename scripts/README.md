# 🛠️ 开发脚本

这个目录包含项目的开发工具和脚本。

## 📁 文件说明

### 核心开发工具
- `dev-commands.sh` - 智能开发命令集
- `fix-hardcoded-values.py` - 硬编码检测和修复工具
- `test-build-locally.sh` - 本地构建测试脚本

### 使用方法

#### 1. 加载开发命令
```bash
source scripts/dev-commands.sh
```

#### 2. 使用智能命令
```bash
# 智能提交
smart_commit "feat: add new feature"

# 安全推送
safe_push

# 完整开发流程
dev_flow "fix: resolve issue"

# 本地测试
local_test

# 快速修复
quick_fix
```

#### 3. 硬编码检测
```bash
python3 scripts/fix-hardcoded-values.py
```

#### 4. 本地构建测试
```bash
./scripts/test-build-locally.sh
```

## 🎯 开发文化

这些工具体现了项目的智能开发文化：
- 自动化优先
- 质量保证
- 快速反馈
- 持续改进

## 📚 更多信息

详细使用指南请参考 `docs/DEVELOPMENT_GUIDE.md`
