#!/bin/bash
# 🔍 模拟 GitHub Actions 构建环境
# 精确复制 CI/CD 环境来诊断构建失败

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 模拟 GitHub Actions 构建环境...${NC}"

# 创建日志目录
mkdir -p ci-logs

# 1. 模拟 GitHub Actions 环境变量
echo -e "${BLUE}1. 设置 GitHub Actions 环境变量...${NC}"

export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="CI Build"
export GITHUB_RUN_ID="test-run-$(date +%s)"
export GITHUB_REPOSITORY="xupeng211/github-notion"
export GITHUB_REF="refs/heads/main"
export RUNNER_OS="Linux"
export RUNNER_ARCH="X64"

echo "✅ GitHub Actions 环境变量已设置"

# 2. 检查当前触发的工作流
echo -e "${BLUE}2. 检查会被触发的工作流...${NC}"

workflows_triggered=()

# 检查 ci-build.yml
if [ -f ".github/workflows/ci-build.yml" ]; then
    if grep -q "push:" .github/workflows/ci-build.yml && grep -q "main" .github/workflows/ci-build.yml; then
        workflows_triggered+=("ci-build.yml")
        echo "✅ ci-build.yml 会被触发"
    fi
fi

# 检查 aws-deploy-robust.yml
if [ -f ".github/workflows/aws-deploy-robust.yml" ]; then
    if grep -q "push:" .github/workflows/aws-deploy-robust.yml; then
        workflows_triggered+=("aws-deploy-robust.yml")
        echo "✅ aws-deploy-robust.yml 会被触发"
    fi
fi

# 检查 optimized-build.yml
if [ -f ".github/workflows/optimized-build.yml" ]; then
    if grep -q "workflow_dispatch" .github/workflows/optimized-build.yml; then
        echo "ℹ️  optimized-build.yml 需要手动触发"
    fi
fi

echo "📋 将被触发的工作流: ${workflows_triggered[*]}"

# 3. 模拟 ci-build.yml 的构建步骤
echo -e "${BLUE}3. 模拟 ci-build.yml 构建步骤...${NC}"

if [[ " ${workflows_triggered[*]} " =~ " ci-build.yml " ]]; then
    echo "🔨 开始模拟 ci-build.yml..."
    
    # 步骤 1: Checkout (已经在本地)
    echo "✅ Step 1: Checkout code"
    
    # 步骤 2: Set up Python
    echo "✅ Step 2: Set up Python 3.11"
    python3 --version
    
    # 步骤 3: Install dependencies
    echo "🔧 Step 3: Install dependencies"
    echo "模拟: pip install -r requirements.txt"
    
    # 检查 requirements.txt
    if [ -f "requirements.txt" ]; then
        echo "检查 requirements.txt 内容..."
        head -10 requirements.txt
        
        # 检查是否有版本冲突
        echo "检查潜在的版本冲突..."
        if pip-compile --dry-run requirements.txt > ci-logs/pip-compile.log 2>&1; then
            echo "✅ 依赖解析成功"
        else
            echo "❌ 依赖解析失败"
            cat ci-logs/pip-compile.log
        fi
    fi
    
    # 步骤 4: Build Docker image
    echo "🐳 Step 4: Build Docker image"
    
    # 检查使用的 Dockerfile
    dockerfile_path="./Dockerfile.github"
    if [ ! -f "$dockerfile_path" ]; then
        echo "❌ Dockerfile 不存在: $dockerfile_path"
        exit 1
    fi
    
    echo "使用 Dockerfile: $dockerfile_path"
    echo "开始构建..."
    
    # 实际构建 Docker 镜像，捕获详细日志
    if docker build -f "$dockerfile_path" -t github-notion-sync:ci-test . > ci-logs/docker-build.log 2>&1; then
        echo "✅ Docker 构建成功"
    else
        echo "❌ Docker 构建失败"
        echo "构建日志:"
        cat ci-logs/docker-build.log
        
        # 分析构建失败的原因
        echo -e "\n${RED}🔍 分析构建失败原因:${NC}"
        
        if grep -q "pip install" ci-logs/docker-build.log; then
            echo "📦 检测到 pip 安装问题"
            grep -A 5 -B 5 "ERROR\|Failed\|error" ci-logs/docker-build.log || true
        fi
        
        if grep -q "COPY\|ADD" ci-logs/docker-build.log; then
            echo "📁 检测到文件复制问题"
            grep -A 3 -B 3 "COPY\|ADD" ci-logs/docker-build.log || true
        fi
        
        if grep -q "RUN" ci-logs/docker-build.log; then
            echo "⚙️ 检测到命令执行问题"
            grep -A 5 -B 5 "RUN.*failed\|RUN.*error" ci-logs/docker-build.log || true
        fi
        
        exit 1
    fi
    
    # 步骤 5: Test container
    echo "🧪 Step 5: Test container"
    
    # 启动容器并测试
    container_name="ci-test-container-$(date +%s)"
    
    if docker run -d --name "$container_name" -p 8080:8000 \
        -e ENVIRONMENT=ci \
        -e GITHUB_TOKEN=placeholder_token \
        -e GITHUB_WEBHOOK_SECRET=placeholder_secret \
        -e NOTION_TOKEN=placeholder_notion \
        -e NOTION_DATABASE_ID=placeholder_db \
        -e DEADLETTER_REPLAY_TOKEN=placeholder_replay \
        github-notion-sync:ci-test > ci-logs/container-start.log 2>&1; then
        
        echo "✅ 容器启动成功"
        
        # 等待应用启动
        echo "等待应用启动..."
        sleep 10
        
        # 检查容器状态
        if docker ps | grep -q "$container_name"; then
            echo "✅ 容器正在运行"
            
            # 获取容器日志
            echo "📋 容器启动日志:"
            docker logs "$container_name" > ci-logs/container-logs.log 2>&1
            cat ci-logs/container-logs.log
            
            # 测试健康检查
            echo "🏥 测试健康检查..."
            if curl -f http://localhost:8080/health > ci-logs/health-check.log 2>&1; then
                echo "✅ 健康检查通过"
                cat ci-logs/health-check.log
            else
                echo "❌ 健康检查失败"
                cat ci-logs/health-check.log
            fi
            
        else
            echo "❌ 容器已停止"
            docker logs "$container_name" > ci-logs/container-crash.log 2>&1
            echo "容器崩溃日志:"
            cat ci-logs/container-crash.log
        fi
        
        # 清理容器
        docker stop "$container_name" 2>/dev/null || true
        docker rm "$container_name" 2>/dev/null || true
        
    else
        echo "❌ 容器启动失败"
        cat ci-logs/container-start.log
        exit 1
    fi
    
    # 清理镜像
    docker rmi github-notion-sync:ci-test 2>/dev/null || true
    
else
    echo "ℹ️  ci-build.yml 不会被触发"
fi

# 4. 生成详细的诊断报告
echo -e "${BLUE}4. 生成诊断报告...${NC}"

cat > ci-logs/github-actions-simulation-report.md << 'EOF'
# 🔍 GitHub Actions 构建模拟报告

## 📋 模拟结果

### 🔧 环境配置
- CI: true
- GitHub Actions: true
- Python 版本: 检查通过
- Docker: 可用

### 📦 依赖检查
- requirements.txt: 存在
- 依赖解析: 检查 pip-compile.log

### 🐳 Docker 构建
- Dockerfile: ./Dockerfile.github
- 构建结果: 检查 docker-build.log
- 容器测试: 检查 container-logs.log

### 🏥 健康检查
- 端点: /health
- 结果: 检查 health-check.log

## 📁 生成的日志文件

1. `pip-compile.log` - 依赖解析日志
2. `docker-build.log` - Docker 构建日志
3. `container-start.log` - 容器启动日志
4. `container-logs.log` - 应用运行日志
5. `health-check.log` - 健康检查日志
6. `container-crash.log` - 容器崩溃日志（如果有）

## 🔧 常见问题排查

### 如果 Docker 构建失败
1. 检查 `docker-build.log` 中的错误信息
2. 验证 requirements.txt 中的依赖版本
3. 确认所有必需文件存在

### 如果容器启动失败
1. 检查 `container-crash.log` 中的错误
2. 验证环境变量配置
3. 检查应用代码中的启动逻辑

### 如果健康检查失败
1. 检查应用是否正确启动
2. 验证端口配置
3. 检查健康检查端点实现

EOF

echo -e "${GREEN}✅ GitHub Actions 模拟完成！${NC}"
echo -e "${BLUE}📄 详细报告: ci-logs/github-actions-simulation-report.md${NC}"
echo -e "${YELLOW}📁 所有日志文件保存在: ci-logs/${NC}"

# 显示关键信息
echo -e "\n${CYAN}🎯 关键信息总结:${NC}"
if [ -f "ci-logs/docker-build.log" ]; then
    if grep -q "Successfully built\|Successfully tagged" ci-logs/docker-build.log; then
        echo -e "${GREEN}✅ Docker 构建: 成功${NC}"
    else
        echo -e "${RED}❌ Docker 构建: 失败${NC}"
        echo "主要错误:"
        grep -i "error\|failed\|fatal" ci-logs/docker-build.log | head -3 || echo "未找到明确错误信息"
    fi
fi

if [ -f "ci-logs/health-check.log" ]; then
    if grep -q '"status":"healthy"' ci-logs/health-check.log; then
        echo -e "${GREEN}✅ 健康检查: 通过${NC}"
    else
        echo -e "${RED}❌ 健康检查: 失败${NC}"
    fi
fi
