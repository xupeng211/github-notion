# 🚨 强制性代码质量规则

> **重要：本文档定义了项目的强制性代码质量规则。所有协作者（包括AI）在提交代码前必须严格遵守这些规则。**

## 📋 必须执行的规则

### ⚡ 提交前强制检查清单

**每次提交代码前，必须按以下顺序执行：**

1. **自动修复格式问题**
   ```bash
   make fix
   ```

2. **运行完整质量检查**
   ```bash
   make check
   ```

3. **确认所有检查通过**
   ```bash
   make lint
   ```

4. **如果仍有错误，运行全自动修复**
   ```bash
   ./fix-code-quality.sh
   ```

### 🔒 Git Hooks 强制执行

项目已配置 Pre-commit hooks，会在每次提交时自动执行：

```bash
# 安装 hooks（首次设置）
pre-commit install

# 手动运行 hooks 检查
pre-commit run --all-files
```

## 📐 代码格式标准

### Python 代码规范

1. **缩进**: 必须使用4个空格，禁止Tab字符
2. **行长**: 最大120字符
3. **导入排序**: 使用isort自动排序
4. **代码格式**: 使用Black自动格式化
5. **空白字符**: 禁止行末空白，文件末尾必须有换行符

### 强制格式化工具

- **Black**: 代码格式化
- **isort**: 导入排序
- **autoflake**: 移除未使用导入
- **flake8**: 代码质量检查

## 🚫 禁止行为

### ❌ 绝对禁止提交

1. **未格式化的代码**
2. **包含Tab缩进的Python文件**
3. **未使用的导入语句**
4. **行末空白字符**
5. **不符合PEP8的代码**

### ❌ 提交前必须修复

1. **f-string缺少占位符**
2. **bare except语句**
3. **过长的代码行（>120字符）**
4. **导入顺序混乱**
5. **变量/函数命名不规范**

## 🤖 AI协作者专用规则

### 📝 代码编辑规则

**当AI修改或创建Python文件时，必须：**

1. **使用edit_file工具后立即执行**：
   ```bash
   make fix
   ```

2. **在提交前必须运行**：
   ```bash
   make check
   ```

3. **如果检查失败，必须修复后再提交**

### 🔄 工作流程

```bash
# AI协作者的标准工作流程
1. 编辑/创建代码文件
2. make fix           # 自动修复格式
3. make lint         # 检查质量
4. 修复剩余问题（如有）
5. git add .
6. git commit       # pre-commit会自动检查
7. git push
```

## 🛠️ 快速修复命令

### 紧急修复

```bash
# 一键修复所有格式问题
./fix-code-quality.sh

# 修复特定文件
black specific_file.py
isort specific_file.py
autoflake --remove-all-unused-imports --in-place specific_file.py
```

### 批量检查

```bash
# 检查所有文件
make check

# 修复所有问题
make fix && make lint
```

## 📊 质量标准

### ✅ 通过标准

- Flake8错误数：**0个**
- Black格式检查：**通过**
- isort导入检查：**通过**
- Pre-commit hooks：**全部通过**

### 🎯 质量目标

1. **零格式错误**：所有代码必须通过Black格式化
2. **零导入错误**：无未使用导入，导入顺序正确
3. **零基础错误**：无Tab缩进、行末空白等问题
4. **统一风格**：整个项目保持一致的代码风格

## 🔧 工具配置文件

项目包含以下配置文件，**禁止随意修改**：

- `.pre-commit-config.yaml` - Pre-commit配置
- `pyproject.toml` - Black和isort配置
- `.flake8` - 代码质量检查配置
- `Makefile` - 便捷命令
- `.vscode/settings.json` - VS Code配置

## ⚠️ 违规处理

### 不合规代码的处理

1. **自动拒绝**：Pre-commit hooks会阻止不合规代码提交
2. **立即修复**：发现问题后必须立即运行修复工具
3. **重新检查**：修复后必须重新运行质量检查

### AI协作者责任

- 每次编辑代码后必须运行质量检查
- 提交前必须确保所有检查通过
- 如果工具修复失败，必须手动修复或报告问题

## 🚀 最佳实践

### 开发环境设置

1. **安装开发工具**：`make install-dev`
2. **设置Pre-commit**：`pre-commit install`
3. **配置IDE**：使用项目提供的配置文件

### 日常工作流程

```bash
# 每天开始工作前
git pull origin main
make clean

# 修改代码后
make check

# 提交前
make fix && make lint && git add . && git commit -m "your message"
```

---

## 📢 重要提醒

**🚨 这些规则是强制性的，不是建议！**

- ✅ 所有代码必须通过质量检查才能提交
- ✅ Pre-commit hooks会自动执行检查
- ✅ AI协作者必须严格遵守这些规则
- ✅ 违规代码会被自动拒绝

**�� 目标：维护高质量、一致性的代码库**
