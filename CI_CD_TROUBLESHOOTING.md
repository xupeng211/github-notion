# 🔧 CI/CD 构建失败故障排查指南

## 🚨 常见失败原因及解决方案

### 1. **Docker 构建超时**

#### 症状
```bash
Error: The operation was canceled.
Step 7/15 : RUN pip install --user --no-warn-script-location
```

#### 解决方案
- ✅ 已添加构建超时设置 (20分钟)
- ✅ 已优化 pip 安装参数 (--timeout=300 --retries=3)
- ✅ 已启用 Docker Buildx 缓存

### 2. **Python 依赖编译失败**

#### 症状
```bash
Building wheel for cryptography (pyproject.toml) ... error
ERROR: Failed building wheel for cryptography
```

#### 解决方案
```bash
# 使用预编译二进制包
pip install --prefer-binary cryptography
```

### 3. **健康检查失败**

#### 症状
```bash
curl: command not found
Container health check failed
```

#### 解决方案
- ✅ 已在 Dockerfile 中安装 curl
- ✅ 已优化健康检查参数

### 4. **容器启动失败**

#### 症状
```bash
docker: Error response from daemon: container failed to start
```

#### 可能原因
- 环境变量缺失
- 端口冲突
- 权限问题

## 🔍 诊断步骤

### 步骤 1: 检查 GitHub Actions 日志
```bash
# 访问 GitHub Actions 页面
https://github.com/你的用户名/你的仓库/actions

# 查看失败的工作流
# 点击失败的 job > 展开失败的步骤
```

### 步骤 2: 本地复现问题
```bash
# 运行本地测试脚本
chmod +x quick-docker-test.sh
./quick-docker-test.sh

# 或使用最小化 Dockerfile
docker build -f Dockerfile.minimal -t test:minimal .
```

### 步骤 3: 检查资源使用
```bash
# 在 CI 中添加资源监控
docker stats --no-stream
free -h
df -h
```

## 🚀 快速修复方案

### 方案 A: 使用最小化构建
```yaml
# 在 .github/workflows/ci.yml 中
- name: "Build Docker Image (Minimal)"
  run: |
    docker build -f Dockerfile.minimal -t ${{ env.IMAGE_LOCAL }} .
```

### 方案 B: 跳过问题步骤
```yaml
# 临时跳过容器测试
- name: "Container Smoke Test"
  if: false  # 临时禁用
  run: |
    # ... 测试代码
```

### 方案 C: 增加重试机制
```yaml
- name: "Build with Retry"
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 30
    max_attempts: 3
    command: docker build -f Dockerfile -t ${{ env.IMAGE_LOCAL }} .
```

## 📊 监控和预防

### 1. 添加构建时间监控
```bash
# 在 CI 脚本中添加
echo "构建开始时间: $(date)"
time docker build -f Dockerfile -t test .
echo "构建结束时间: $(date)"
```

### 2. 定期更新依赖
```bash
# 每月检查依赖更新
pip list --outdated
```

### 3. 缓存优化
```yaml
# 使用 GitHub Actions 缓存
- name: Cache Docker layers
  uses: actions/cache@v3
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-
```

## 🎯 下一步行动

### 立即执行
1. **提交修复**: 推送当前修复到 main 分支
2. **观察结果**: 查看 CI/CD 是否成功
3. **如果仍失败**: 使用 Dockerfile.minimal

### 备用方案
```bash
# 如果主 Dockerfile 仍有问题，切换到最小版本
mv Dockerfile Dockerfile.full
mv Dockerfile.minimal Dockerfile
git add . && git commit -m "fix: use minimal Dockerfile for CI stability"
git push origin main
```

## 📞 获取帮助

如果问题持续存在：

1. **查看详细日志**: GitHub Actions > 失败的 job > 下载日志
2. **检查系统状态**: [GitHub Status](https://www.githubstatus.com/)
3. **社区支持**: GitHub Discussions 或 Stack Overflow

---

**最后更新**: $(date)
**状态**: 🔧 修复中，等待验证
