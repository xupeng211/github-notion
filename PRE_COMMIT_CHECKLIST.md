# 📋 推送代码前检查清单

> **必读**: 在推送代码到仓库前，请务必完成以下所有检查项，确保代码质量和系统稳定性。

## 🧪 **第一步：运行完整测试套件**

```bash
# 运行完整测试（必需）
python scripts/run_full_tests.py
```

**期望结果**: 
- ✅ 所有测试通过
- ✅ 成功率 100%
- ✅ 显示 "代码可以安全推送到仓库"

## 🔧 **第二步：架构验证**

```bash
# 运行架构验证（必需）
python scripts/validate_fixes.py
```

**期望结果**:
- ✅ 9/9 测试通过
- ✅ "🎉 所有测试通过！架构修复验证成功"

## 📝 **第三步：代码质量检查**

### 语法和格式检查
```bash
# 代码格式检查（推荐）
python -m flake8 app/ --max-line-length=120 --ignore=E203,W503

# 类型检查（推荐）
python -m mypy app/ --ignore-missing-imports
```

### 导入检查
```bash
# 验证关键模块可正常导入
python -c "
import app.server
import app.service  
import app.models
import app.notion
import app.github
print('✅ 所有模块导入成功')
"
```

## 🔍 **第四步：安全检查**

### 敏感信息检查
- [ ] **检查 .env 文件未被提交**
  ```bash
  git status | grep -v "\.env"
  ```

- [ ] **检查代码中无硬编码密钥**
  ```bash
  grep -r "ghp_\|secret_\|token.*=" app/ || echo "✅ 无硬编码密钥"
  ```

- [ ] **检查 .gitignore 包含敏感文件**
  ```bash
  grep -E "\.env|\.log|data/.*\.db" .gitignore || echo "⚠️ 需要更新 .gitignore"
  ```

## 📚 **第五步：文档检查**

- [ ] **README 文档是否需要更新**
- [ ] **API 文档是否需要更新** 
- [ ] **配置示例文件是否最新**
  ```bash
  # 检查 env.example 是否包含新增的环境变量
  diff <(grep "^[A-Z]" env.example | sort) <(grep "getenv" app/*.py | sed 's/.*getenv("\([^"]*\)".*/\1/' | sort -u)
  ```

## 🏗️ **第六步：部署验证**

### 本地部署测试
```bash
# 测试自动化启动流程
python scripts/start_service.py &
SERVER_PID=$!

# 等待服务启动
sleep 5

# 测试健康检查
curl -s http://localhost:8000/health | grep '"status".*"healthy"' && echo "✅ 服务启动成功"

# 清理
kill $SERVER_PID
```

### 配置文件验证
- [ ] **监控配置文件语法正确**
  ```bash
  # 验证 Prometheus 配置
  promtool check config monitoring/prometheus.yml
  
  # 验证告警规则
  promtool check rules monitoring/alert_rules.yml
  ```

## ⚡ **第七步：性能检查**

### 启动时间测试
```bash
# 测试服务启动时间
time python scripts/start_service.py --test-startup
```

### 内存泄漏检查
```bash
# 简单的内存使用检查
python -c "
import psutil
import app.server
print(f'✅ 模块加载后内存使用: {psutil.virtual_memory().percent:.1f}%')
"
```

## 📊 **第八步：版本和变更管理**

### 版本标记
- [ ] **更新版本号** (如有需要)
- [ ] **更新 CHANGELOG.md** (如有需要)
- [ ] **标记重要变更** (如有 breaking changes)

### Git 提交检查
```bash
# 检查暂存的文件
git status

# 检查 diff
git diff --cached

# 确保提交信息清晰
git log --oneline -5
```

## 🚀 **最终推送检查**

### 推送前最后确认
- [ ] ✅ 完整测试套件通过
- [ ] ✅ 架构验证通过  
- [ ] ✅ 代码质量检查通过
- [ ] ✅ 安全检查通过
- [ ] ✅ 文档已更新
- [ ] ✅ 部署验证通过
- [ ] ✅ 性能检查通过
- [ ] ✅ 版本管理完成

### 推送命令
```bash
# 推送到远程仓库
git push origin main

# 如果有标签
git push origin --tags
```

## 🚨 **紧急修复流程**

如果发现问题需要紧急修复：

1. **立即回滚**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **修复验证**
   ```bash
   # 修复代码后重新运行测试
   python scripts/run_full_tests.py
   ```

3. **重新推送**
   ```bash
   git add .
   git commit -m "fix: 紧急修复问题"
   git push origin main
   ```

## 📞 **支持和帮助**

### 测试失败处理
- **架构测试失败**: 检查 `scripts/validate_fixes.py` 输出
- **API 测试失败**: 检查服务启动日志
- **数据库测试失败**: 确认 alembic 迁移文件

### 常用调试命令
```bash
# 查看详细测试报告
cat test_report.json | jq '.details[] | select(.passed == false)'

# 查看服务启动日志
python scripts/start_service.py 2>&1 | tee startup.log

# 快速健康检查
curl -s http://localhost:8000/health | jq '.'
```

---

## 📋 **快速检查命令**

```bash
#!/bin/bash
# 保存为 check_before_commit.sh

echo "🧪 运行完整测试..."
python scripts/run_full_tests.py || exit 1

echo "🔧 架构验证..."
python scripts/validate_fixes.py || exit 1

echo "🔍 安全检查..."
git status | grep "\.env" && echo "❌ .env 文件不应提交" && exit 1

echo "✅ 所有检查通过！可以安全推送代码。"
```

**使用方法**:
```bash
chmod +x check_before_commit.sh
./check_before_commit.sh && git push origin main
```

---

**🎯 记住**: 质量第一！宁可多花几分钟测试，也不要推送有问题的代码到生产环境。 