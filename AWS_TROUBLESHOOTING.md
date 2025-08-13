# 🔧 AWS 服务器连接问题解决指南

## 📊 当前状态

✅ **好消息**: 
- Docker 镜像构建和推送**完全成功**
- 服务器 13.209.76.79 在线且可以 ping 通
- CI/CD 流水线的前 3 个阶段都正常

❌ **问题**: 
- SSH 连接超时 (端口 22 无法访问)
- AWS 部署阶段失败
- AWS 服务器 IP 地址已更新为 3.35.106.116

## 🎯 解决方案

### 方案 1: 修复 AWS 安全组配置 (推荐)

**步骤 1: 登录 AWS 控制台**
```
1. 访问: https://console.aws.amazon.com/ec2/
2. 选择您的区域 (应该是 ap-northeast-2 首尔)
3. 点击 "实例" 找到您的 EC2 实例
4. 选择实例，点击 "安全" 选项卡
5. 点击安全组链接
```

**步骤 2: 检查和修改安全组规则**
```
当前问题: SSH 端口 22 可能没有正确开放

需要添加的规则:
类型: SSH
协议: TCP
端口范围: 22
源: 0.0.0.0/0  (或者您的 IP 地址)

类型: 自定义 TCP
协议: TCP  
端口范围: 8000
源: 0.0.0.0/0
```

### 方案 2: 检查 EC2 实例状态

**可能的问题:**
1. **实例未运行** - 检查实例状态是否为 "running"
2. **密钥对错误** - 确认使用正确的 .pem 文件
3. **用户名错误** - Ubuntu 实例应该使用 "ubuntu" 用户
4. **实例防火墙** - 实例内部 ufw 防火墙阻止连接

### 方案 3: 手动部署验证 (临时方案)

如果 AWS 连接问题暂时无法解决，您可以手动部署：

```bash
# 1. 从 GitHub Container Registry 拉取镜像
docker pull ghcr.io/xupeng211/gitee-notion:latest

# 2. 直接在服务器上运行
docker run -d \
  --name gitee-notion-app \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e LOG_LEVEL=INFO \
  -e ENVIRONMENT=production \
  ghcr.io/xupeng211/gitee-notion:latest

# 3. 验证服务
curl http://localhost:8000/health
```

## 🔍 详细排查步骤

### 1. 验证 AWS 实例状态
```bash
# 在 AWS 控制台检查:
- 实例状态: running
- 系统检查: 2/2 checks passed  
- 实例可达性: reachable
- 系统状态: ok
```

### 2. 验证安全组配置
```bash
# 必需的入站规则:
SSH (22)     | TCP | 0.0.0.0/0     | 允许 SSH 访问
HTTP (8000)  | TCP | 0.0.0.0/0     | 允许应用访问
```

### 3. 验证网络 ACL
```bash
# 确认子网的网络 ACL 允许:
- 入站: TCP 22, TCP 8000
- 出站: All traffic
```

### 4. 验证密钥对
```bash
# GitHub Secrets 中的 AWS_PRIVATE_KEY 应该:
- 包含完整的 .pem 文件内容
- 以 "-----BEGIN RSA PRIVATE KEY-----" 开头
- 以 "-----END RSA PRIVATE KEY-----" 结尾
- 没有额外的空格或换行
```

## 🚀 快速修复建议

### 最可能的解决方案 (按优先级):

1. **修复安全组** (90% 可能性)
   - 添加 SSH (22) 入站规则
   - 源设置为 0.0.0.0/0

2. **检查实例状态** (5% 可能性)  
   - 确认实例正在运行
   - 重启实例如果需要

3. **更新 GitHub Secret** (5% 可能性)
   - 重新复制 .pem 文件内容到 AWS_PRIVATE_KEY

## 📋 验证清单

完成修复后，请验证:
- [ ] AWS 安全组包含 SSH (22) 规则
- [ ] AWS 安全组包含 HTTP (8000) 规则  
- [ ] EC2 实例状态为 "running"
- [ ] GitHub Secret AWS_PRIVATE_KEY 已正确设置
- [ ] 重新运行 GitHub Actions 工作流
- [ ] 部署成功，服务可访问

## 🎉 成功指标

修复后您应该看到:
- ✅ 所有 4 个 CI/CD 阶段都是绿色
- ✅ 可以访问 http://3.35.106.116:8000/health
- ✅ 可以访问 http://3.35.106.116:8000/docs
- ✅ 企业级 CI/CD 流水线完全正常工作

---

**重要提醒**: 您的 Docker 镜像构建完全成功！问题只是 AWS 网络配置，很容易修复。 