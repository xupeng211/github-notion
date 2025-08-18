#!/bin/bash
# 🔍 深度 CI/CD 调试 - 精确复制 GitHub Actions 失败场景
# 逐步分析每个构建阶段的详细日志

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 深度 CI/CD 调试分析...${NC}"

# 创建详细日志目录
mkdir -p deep-ci-logs/{build,runtime,network,system}

# 1. 检查当前 Git 状态和最新提交
echo -e "${BLUE}1. 检查 Git 状态和最新提交...${NC}"
git log --oneline -3 > deep-ci-logs/git-status.log
echo "最新提交:"
cat deep-ci-logs/git-status.log

# 2. 分析会被触发的工作流
echo -e "${BLUE}2. 分析 GitHub Actions 工作流...${NC}"

# 检查 ci-build.yml 的具体内容
if [ -f ".github/workflows/ci-build.yml" ]; then
    echo "📋 分析 ci-build.yml 工作流..."
    
    # 提取关键步骤
    echo "触发条件:" > deep-ci-logs/workflow-analysis.log
    grep -A 5 "on:" .github/workflows/ci-build.yml >> deep-ci-logs/workflow-analysis.log
    
    echo -e "\n构建步骤:" >> deep-ci-logs/workflow-analysis.log
    grep -n "name:\|run:\|uses:" .github/workflows/ci-build.yml >> deep-ci-logs/workflow-analysis.log
    
    echo "工作流分析完成，详见: deep-ci-logs/workflow-analysis.log"
fi

# 3. 精确模拟 GitHub Actions 环境
echo -e "${BLUE}3. 精确模拟 GitHub Actions 环境...${NC}"

# 设置完全相同的环境变量
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="CI Build"
export GITHUB_RUN_ID="debug-$(date +%s)"
export GITHUB_REPOSITORY="xupeng211/github-notion"
export GITHUB_REF="refs/heads/main"
export RUNNER_OS="Linux"
export RUNNER_ARCH="X64"
export RUNNER_TEMP="/tmp"
export RUNNER_WORKSPACE="/home/runner/work"

# GitHub Actions 默认环境变量
export AWS_HOST="3.35.106.116"
export APP_PORT="8000"
export APP_DIR="/opt/github-notion-sync"
export SERVICE_NAME="github-notion-sync"

echo "✅ GitHub Actions 环境变量已设置"

# 4. 逐步执行构建过程，捕获每个阶段的详细日志
echo -e "${BLUE}4. 逐步执行构建过程...${NC}"

# Step 1: Python 环境检查
echo "🐍 Step 1: Python 环境检查..."
python3 --version > deep-ci-logs/python-version.log 2>&1
pip --version >> deep-ci-logs/python-version.log 2>&1
echo "Python 环境信息已保存"

# Step 2: 依赖分析
echo "📦 Step 2: 依赖分析..."
echo "检查 requirements.txt..." > deep-ci-logs/dependencies.log
if [ -f "requirements.txt" ]; then
    echo "=== requirements.txt 内容 ===" >> deep-ci-logs/dependencies.log
    cat requirements.txt >> deep-ci-logs/dependencies.log
    
    echo -e "\n=== 检查依赖冲突 ===" >> deep-ci-logs/dependencies.log
    # 模拟 pip install 检查
    python3 -m pip check >> deep-ci-logs/dependencies.log 2>&1 || echo "发现依赖冲突" >> deep-ci-logs/dependencies.log
    
    echo -e "\n=== 当前已安装包 ===" >> deep-ci-logs/dependencies.log
    pip list >> deep-ci-logs/dependencies.log 2>&1
fi

# Step 3: Docker 构建详细分析
echo "🐳 Step 3: Docker 构建详细分析..."

# 检查 Dockerfile
dockerfile_path="./Dockerfile.github"
echo "使用 Dockerfile: $dockerfile_path"

if [ ! -f "$dockerfile_path" ]; then
    echo "❌ Dockerfile 不存在: $dockerfile_path"
    exit 1
fi

echo "=== Dockerfile 内容分析 ===" > deep-ci-logs/build/dockerfile-analysis.log
cat "$dockerfile_path" >> deep-ci-logs/build/dockerfile-analysis.log

# 执行 Docker 构建，捕获详细输出
echo "开始 Docker 构建..."
image_name="github-notion-debug:$(date +%s)"

if docker build --progress=plain --no-cache -f "$dockerfile_path" -t "$image_name" . > deep-ci-logs/build/docker-build-full.log 2>&1; then
    echo "✅ Docker 构建成功"
    
    # 分析构建的镜像
    echo "=== 镜像信息 ===" > deep-ci-logs/build/image-info.log
    docker images "$image_name" >> deep-ci-logs/build/image-info.log
    docker inspect "$image_name" >> deep-ci-logs/build/image-info.log 2>&1
    
else
    echo "❌ Docker 构建失败"
    echo "构建失败日志:"
    tail -50 deep-ci-logs/build/docker-build-full.log
    
    # 分析构建失败的具体原因
    echo -e "\n${RED}🔍 构建失败分析:${NC}"
    
    if grep -q "pip install" deep-ci-logs/build/docker-build-full.log; then
        echo "📦 检测到 pip 安装问题:"
        grep -A 10 -B 5 "ERROR\|Failed\|error" deep-ci-logs/build/docker-build-full.log | head -20
    fi
    
    if grep -q "COPY\|ADD" deep-ci-logs/build/docker-build-full.log; then
        echo "📁 检测到文件复制问题:"
        grep -A 5 -B 5 "COPY\|ADD.*failed\|No such file" deep-ci-logs/build/docker-build-full.log
    fi
    
    if grep -q "RUN.*failed\|command not found" deep-ci-logs/build/docker-build-full.log; then
        echo "⚙️ 检测到命令执行问题:"
        grep -A 5 -B 5 "RUN.*failed\|command not found" deep-ci-logs/build/docker-build-full.log
    fi
    
    exit 1
fi

# Step 4: 容器运行时测试
echo "🧪 Step 4: 容器运行时测试..."

container_name="debug-container-$(date +%s)"

# 启动容器，使用与 GitHub Actions 相同的环境变量
echo "启动容器进行测试..."
if docker run -d --name "$container_name" \
    -p 8090:8000 \
    -e CI=true \
    -e GITHUB_ACTIONS=true \
    -e ENVIRONMENT=ci \
    -e GITHUB_TOKEN=placeholder_token \
    -e GITHUB_WEBHOOK_SECRET=placeholder_secret \
    -e NOTION_TOKEN=placeholder_notion \
    -e NOTION_DATABASE_ID=placeholder_db \
    -e DEADLETTER_REPLAY_TOKEN=placeholder_replay \
    -e LOG_LEVEL=DEBUG \
    "$image_name" > deep-ci-logs/runtime/container-start.log 2>&1; then
    
    echo "✅ 容器启动成功"
    
    # 等待应用启动
    echo "等待应用启动..."
    sleep 15
    
    # 检查容器状态
    echo "=== 容器状态 ===" > deep-ci-logs/runtime/container-status.log
    docker ps | grep "$container_name" >> deep-ci-logs/runtime/container-status.log
    docker stats --no-stream "$container_name" >> deep-ci-logs/runtime/container-status.log 2>&1
    
    # 获取详细的容器日志
    echo "=== 容器启动日志 ===" > deep-ci-logs/runtime/container-logs.log
    docker logs "$container_name" >> deep-ci-logs/runtime/container-logs.log 2>&1
    
    echo "容器日志已保存，最新 20 行:"
    tail -20 deep-ci-logs/runtime/container-logs.log
    
    # 检查容器是否还在运行
    if docker ps | grep -q "$container_name"; then
        echo "✅ 容器正在运行"
        
        # 测试网络连接
        echo "🌐 Step 5: 网络连接测试..."
        
        # 测试基础连接
        echo "=== 基础连接测试 ===" > deep-ci-logs/network/connectivity.log
        if curl -v http://localhost:8090/ >> deep-ci-logs/network/connectivity.log 2>&1; then
            echo "✅ 基础连接成功"
        else
            echo "❌ 基础连接失败"
        fi
        
        # 测试健康检查端点
        echo -e "\n=== 健康检查测试 ===" >> deep-ci-logs/network/connectivity.log
        
        # 测试标准健康检查
        echo "测试标准健康检查 (/health):"
        if curl -v -m 30 http://localhost:8090/health > deep-ci-logs/network/health-standard.log 2>&1; then
            echo "✅ 标准健康检查响应"
            echo "响应内容:"
            cat deep-ci-logs/network/health-standard.log | grep -A 1000 "^{"
        else
            echo "❌ 标准健康检查失败"
            echo "错误详情:"
            cat deep-ci-logs/network/health-standard.log
        fi
        
        # 测试 CI 健康检查
        echo -e "\n测试 CI 健康检查 (/health/ci):"
        if curl -v -m 30 http://localhost:8090/health/ci > deep-ci-logs/network/health-ci.log 2>&1; then
            echo "✅ CI 健康检查响应"
            echo "响应内容:"
            cat deep-ci-logs/network/health-ci.log | grep -A 1000 "^{"
        else
            echo "❌ CI 健康检查失败"
            echo "错误详情:"
            cat deep-ci-logs/network/health-ci.log
        fi
        
        # 检查应用内部状态
        echo "🔍 Step 6: 应用内部状态检查..."
        
        # 进入容器检查内部状态
        echo "=== 容器内部检查 ===" > deep-ci-logs/system/internal-check.log
        docker exec "$container_name" ps aux >> deep-ci-logs/system/internal-check.log 2>&1
        docker exec "$container_name" netstat -tlnp >> deep-ci-logs/system/internal-check.log 2>&1
        docker exec "$container_name" ls -la /app >> deep-ci-logs/system/internal-check.log 2>&1
        
        echo "内部状态检查完成"
        
    else
        echo "❌ 容器已停止"
        echo "容器退出原因:"
        docker logs "$container_name" | tail -20
        
        # 检查容器退出状态
        exit_code=$(docker inspect "$container_name" --format='{{.State.ExitCode}}')
        echo "容器退出码: $exit_code"
    fi
    
    # 清理容器
    docker stop "$container_name" 2>/dev/null || true
    docker rm "$container_name" 2>/dev/null || true
    
else
    echo "❌ 容器启动失败"
    cat deep-ci-logs/runtime/container-start.log
fi

# 清理镜像
docker rmi "$image_name" 2>/dev/null || true

# 7. 生成综合分析报告
echo -e "${BLUE}7. 生成综合分析报告...${NC}"

cat > deep-ci-logs/comprehensive-analysis.md << 'EOF'
# 🔍 深度 CI/CD 调试综合分析报告

## 📋 调试结果总览

### 🔧 环境信息
- Git 状态: 检查 git-status.log
- Python 版本: 检查 python-version.log
- 依赖状态: 检查 dependencies.log

### 🐳 Docker 构建分析
- Dockerfile 分析: build/dockerfile-analysis.log
- 完整构建日志: build/docker-build-full.log
- 镜像信息: build/image-info.log

### 🧪 运行时测试
- 容器启动: runtime/container-start.log
- 容器状态: runtime/container-status.log
- 应用日志: runtime/container-logs.log

### 🌐 网络连接测试
- 连接性测试: network/connectivity.log
- 标准健康检查: network/health-standard.log
- CI 健康检查: network/health-ci.log

### 🔍 系统内部检查
- 内部状态: system/internal-check.log

## 🎯 关键问题识别

### 如果 Docker 构建失败
1. 检查 build/docker-build-full.log 中的具体错误
2. 验证 requirements.txt 中的依赖版本
3. 确认所有必需文件存在

### 如果容器启动失败
1. 检查 runtime/container-logs.log 中的启动错误
2. 验证环境变量配置
3. 检查端口冲突

### 如果健康检查失败
1. 比较 network/health-standard.log 和 network/health-ci.log
2. 检查应用是否正确监听端口
3. 验证健康检查端点实现

## 💡 修复建议

基于发现的具体问题，提供针对性的修复方案。

EOF

echo -e "${GREEN}✅ 深度调试完成！${NC}"
echo -e "${BLUE}📄 综合报告: deep-ci-logs/comprehensive-analysis.md${NC}"
echo -e "${YELLOW}📁 所有详细日志保存在: deep-ci-logs/${NC}"

# 显示关键发现
echo -e "\n${CYAN}🎯 关键发现总结:${NC}"

if [ -f "deep-ci-logs/build/docker-build-full.log" ]; then
    if grep -q "Successfully built\|Successfully tagged" deep-ci-logs/build/docker-build-full.log; then
        echo -e "${GREEN}✅ Docker 构建: 成功${NC}"
    else
        echo -e "${RED}❌ Docker 构建: 失败${NC}"
        echo "主要错误:"
        grep -i "error\|failed\|fatal" deep-ci-logs/build/docker-build-full.log | head -3 || echo "未找到明确错误信息"
    fi
fi

if [ -f "deep-ci-logs/network/health-ci.log" ]; then
    if grep -q '"status":"healthy"' deep-ci-logs/network/health-ci.log; then
        echo -e "${GREEN}✅ CI 健康检查: 通过${NC}"
    else
        echo -e "${RED}❌ CI 健康检查: 失败${NC}"
        if grep -q "Connection refused\|timeout" deep-ci-logs/network/health-ci.log; then
            echo "原因: 连接被拒绝或超时"
        fi
    fi
fi

echo -e "\n${PURPLE}🔍 请查看详细日志文件以获取更多信息${NC}"
