# 🎯 优先级执行检查清单

## 🔴 高优先级 - 立即执行 (已完成 ✅)

### ✅ 步骤1: 提交关键修复
- [x] 修复Prometheus指标冲突 (`deadletter_queue_size` → `deadletter_queue_size_by_provider`)
- [x] Git提交修复: `git add app/enhanced_metrics.py`
- [x] 提交信息: "修复: Prometheus指标重复定义冲突"

### ✅ 步骤2: 推送代码
- [x] 推送到GitHub: `git push github main`
- [x] 触发CI/CD流水线

### ✅ 步骤3: 监控CI/CD (第一次)
- [x] 监控链接: https://github.com/xupeng211/github-notion/actions
- [x] **发现问题**: CI/CD构建失败 - Docker镜像构建失败

### ✅ 步骤3.1: 问题诊断和修复
- [x] **问题定位**: 发现第二个重复的Prometheus指标 `deadletter_queue_size`
- [x] **完整修复**: 重命名两个重复指标
  - `deadletter_queue_size` (基础) → `deadletter_queue_size_basic`
  - `deadletter_queue_size` (分组) → `deadletter_queue_size_by_provider`
- [x] **验证修复**: 本地测试应用启动正常
- [x] **重新推送**: 提交完整修复到GitHub

---

## 🟡 中优先级 - 短期执行 (15分钟内)

### 📋 步骤4: 验证最终CI/CD成功
**监控链接:** https://github.com/xupeng211/github-notion/actions
**最新提交:** e6abd3d - 完全解决Prometheus指标重复定义问题

**检查项目:**
- [ ] 所有测试阶段 (test) 通过
- [ ] Docker构建 (build) 成功
- [ ] 镜像推送到 ghcr.io 完成
- [ ] 部署验证通过

**预期:** 📈 成功率应达到95%+（已修复根本原因）

### 📋 步骤5: 配置Docker Desktop WSL集成
**操作步骤:**
- [ ] 打开Docker Desktop → Settings
- [ ] 导航到 Resources → WSL Integration
- [ ] 启用 'Enable integration with my default WSL distro'
- [ ] 启用当前Ubuntu发行版
- [ ] Apply & Restart

**验证:**
```bash
docker --version
docker run hello-world
```

### 📋 步骤6: 执行完整本地测试
**使用创建的脚本:**
```bash
./quick-docker-test.sh
```

**预期结果:**
- [ ] Docker镜像构建成功
- [ ] 容器启动正常
- [ ] 健康检查通过

---

## 🟢 低优先级 - 长期优化 (30分钟内)

### 📋 步骤7: 文档更新
- [ ] 记录修复过程到CHANGELOG.md
- [ ] 更新DEPLOYMENT_GUIDE.md
- [ ] 创建故障排除文档

### 📋 步骤8: 建立最佳实践
- [ ] 制定本地验证SOP
- [ ] 更新pre-commit配置
- [ ] 设置监控告警

---

## 🎯 成功标准

### 短期目标 (今天完成)
- [ ] **CI/CD构建100%成功**
- [ ] **Docker本地测试通过**
- [ ] **应用正常启动和健康检查**

### 长期目标 (本周完成)
- [ ] Docker Desktop完全配置
- [ ] 文档更新完成
- [ ] 监控和告警设置

---

## 🚨 故障排除

### 如果CI/CD仍然失败:
1. 检查GitHub Actions日志
2. 查看Docker构建步骤具体错误
3. 验证环境变量配置
4. 检查依赖包冲突

### 如果本地Docker测试失败:
1. 确认Docker Desktop WSL集成正确
2. 检查端口冲突 (8003)
3. 查看容器日志: `docker logs quick-test`
4. 验证环境变量设置

---

## 📞 下一步联系点

**当前状态**: 等待CI/CD执行结果
**监控链接**: https://github.com/xupeng211/github-notion/actions
**预计完成时间**: 3-5分钟

**如需支持**: 提供CI/CD日志或Docker错误信息
