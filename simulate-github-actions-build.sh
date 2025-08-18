#!/bin/bash
# 🔍 模拟 GitHub Actions 构建过程
# 精确复现远程构建环境和步骤

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 模拟 GitHub Actions 构建过程...${NC}"

# 创建模拟目录
mkdir -p github-actions-simulation

# 1. 模拟 GitHub Actions 环境变量
echo -e "${BLUE}1. 设置 GitHub Actions 环境变量...${NC}"

export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="Build and Deploy"
export GITHUB_RUN_ID="simulation-$(date +%s)"
export GITHUB_REPOSITORY="xupeng211/github-notion"
export GITHUB_REF="refs/heads/main"
export GITHUB_SHA=$(git rev-parse HEAD)
export GITHUB_ACTOR="xupeng211"
export RUNNER_OS="Linux"
export RUNNER_ARCH="X64"

# 模拟工作流环境变量
export REGISTRY="ghcr.io"
export IMAGE_NAME="xupeng211/github-notion"

echo "GitHub Actions 环境变量已设置"

# 2. 检查 Dockerfile.github
echo -e "${BLUE}2. 检查 Dockerfile.github...${NC}"

if [ ! -f "Dockerfile.github" ]; then
    echo -e "${RED}❌ Dockerfile.github 不存在${NC}"
    exit 1
else
    echo "✅ Dockerfile.github 存在"
    
    # 检查 Dockerfile 语法
    echo "检查 Dockerfile 语法..."
    if docker build --dry-run -f Dockerfile.github . > /dev/null 2>&1; then
        echo "✅ Dockerfile 语法正确"
    else
        echo "❌ Dockerfile 语法错误"
        docker build --dry-run -f Dockerfile.github . 2>&1 | head -20
    fi
fi

# 3. 模拟 Docker 构建步骤
echo -e "${BLUE}3. 模拟 Docker 构建步骤...${NC}"

# 生成模拟的镜像标签
TIMESTAMP=$(date +%Y%m%d%H%M%S)
IMAGE_TAG="ghcr.io/xupeng211/github-notion:main-${GITHUB_SHA:0:7}"
LATEST_TAG="ghcr.io/xupeng211/github-notion:latest"

echo "构建镜像标签: $IMAGE_TAG"
echo "最新标签: $LATEST_TAG"

# 开始构建
echo "开始 Docker 构建..."
build_log="github-actions-simulation/docker-build.log"

echo "=== Docker 构建日志 ===" > "$build_log"
echo "时间: $(date)" >> "$build_log"
echo "镜像标签: $IMAGE_TAG" >> "$build_log"
echo "Dockerfile: Dockerfile.github" >> "$build_log"
echo "" >> "$build_log"

# 执行实际构建
if timeout 600 docker build \
    --progress=plain \
    --platform linux/amd64 \
    -f Dockerfile.github \
    -t "$IMAGE_TAG" \
    -t "$LATEST_TAG" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    . >> "$build_log" 2>&1; then
    
    echo "✅ Docker 构建成功"
    
    # 4. 测试构建的镜像
    echo -e "${BLUE}4. 测试构建的镜像...${NC}"
    
    container_name="github-actions-test-$(date +%s)"
    test_log="github-actions-simulation/container-test.log"
    
    echo "=== 容器测试日志 ===" > "$test_log"
    echo "容器名称: $container_name" >> "$test_log"
    echo "镜像: $IMAGE_TAG" >> "$test_log"
    echo "" >> "$test_log"
    
    # 启动容器
    if docker run -d --name "$container_name" \
        -p 8092:8000 \
        -e ENVIRONMENT=ci \
        -e GITHUB_TOKEN=placeholder_token \
        -e GITHUB_WEBHOOK_SECRET=placeholder_secret \
        -e NOTION_TOKEN=placeholder_notion \
        -e NOTION_DATABASE_ID=placeholder_db \
        -e DEADLETTER_REPLAY_TOKEN=placeholder_replay \
        "$IMAGE_TAG" >> "$test_log" 2>&1; then
        
        echo "✅ 容器启动成功"
        
        # 等待应用启动
        echo "等待应用启动..."
        sleep 20
        
        # 检查容器状态
        if docker ps | grep -q "$container_name"; then
            echo "✅ 容器正在运行"
            
            # 获取容器日志
            echo "=== 容器启动日志 ===" >> "$test_log"
            docker logs "$container_name" >> "$test_log" 2>&1
            
            # 5. 模拟健康检查
            echo -e "${BLUE}5. 模拟健康检查...${NC}"
            
            health_log="github-actions-simulation/health-check.log"
            echo "=== 健康检查日志 ===" > "$health_log"
            
            # 检查 Docker 健康检查状态
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
            echo "Docker 健康检查状态: $health_status" >> "$health_log"
            echo "Docker 健康检查状态: $health_status"
            
            # CI 健康检查
            echo "测试 CI 健康检查..." >> "$health_log"
            if curl -f -m 15 http://localhost:8092/health/ci > /tmp/ci-health-sim.json 2>&1; then
                echo "✅ CI 健康检查成功" >> "$health_log"
                echo "✅ CI 健康检查成功"
                
                # 检查响应内容
                response=$(cat /tmp/ci-health-sim.json)
                echo "响应: $response" >> "$health_log"
                
                if echo "$response" | grep -q '"status":"healthy"'; then
                    echo "✅ 状态正确: healthy" >> "$health_log"
                    echo "✅ 状态正确: healthy"
                    ci_health_success=true
                else
                    echo "❌ 状态不正确" >> "$health_log"
                    echo "❌ 状态不正确"
                    ci_health_success=false
                fi
            else
                echo "❌ CI 健康检查失败" >> "$health_log"
                echo "❌ CI 健康检查失败"
                curl -v -m 15 http://localhost:8092/health/ci >> "$health_log" 2>&1 || true
                ci_health_success=false
            fi
            
            # 标准健康检查
            echo "测试标准健康检查..." >> "$health_log"
            if curl -f -m 15 http://localhost:8092/health > /tmp/standard-health-sim.json 2>&1; then
                echo "✅ 标准健康检查成功" >> "$health_log"
                echo "✅ 标准健康检查成功"
                standard_health_success=true
            else
                echo "❌ 标准健康检查失败" >> "$health_log"
                echo "❌ 标准健康检查失败"
                standard_health_success=false
            fi
            
        else
            echo "❌ 容器已停止"
            docker logs "$container_name" >> "$test_log" 2>&1 || true
            ci_health_success=false
            standard_health_success=false
        fi
        
        # 清理容器
        docker stop "$container_name" 2>/dev/null || true
        docker rm "$container_name" 2>/dev/null || true
        
    else
        echo "❌ 容器启动失败"
        cat "$test_log"
        ci_health_success=false
        standard_health_success=false
    fi
    
    # 清理镜像
    docker rmi "$IMAGE_TAG" "$LATEST_TAG" 2>/dev/null || true
    
else
    echo "❌ Docker 构建失败"
    echo "构建错误:"
    tail -30 "$build_log"
    
    # 分析构建失败原因
    echo -e "${BLUE}6. 分析构建失败原因...${NC}"
    
    failure_analysis="github-actions-simulation/build-failure-analysis.log"
    echo "=== 构建失败分析 ===" > "$failure_analysis"
    
    # 检查常见错误
    if grep -q "pip.*failed\|pip.*error" "$build_log"; then
        echo "🔍 检测到 pip 安装错误" >> "$failure_analysis"
        grep -A 10 -B 5 "pip.*failed\|pip.*error" "$build_log" >> "$failure_analysis"
    fi
    
    if grep -q "COPY.*failed\|No such file" "$build_log"; then
        echo "🔍 检测到文件复制错误" >> "$failure_analysis"
        grep -A 5 -B 5 "COPY.*failed\|No such file" "$build_log" >> "$failure_analysis"
    fi
    
    if grep -q "requirements.txt" "$build_log"; then
        echo "🔍 检测到依赖问题" >> "$failure_analysis"
        grep -A 10 -B 5 "requirements.txt" "$build_log" >> "$failure_analysis"
    fi
    
    # 获取最后的错误
    echo "=== 最后的错误信息 ===" >> "$failure_analysis"
    tail -20 "$build_log" >> "$failure_analysis"
    
    echo "构建失败分析已保存到: $failure_analysis"
    exit 1
fi

# 7. 生成模拟报告
echo -e "${BLUE}7. 生成模拟报告...${NC}"

cat > github-actions-simulation/simulation-report.md << EOF
# 🔍 GitHub Actions 构建模拟报告

## 📋 模拟结果

### 🐳 Docker 构建
- 状态: $([ -f "$build_log" ] && grep -q "✅ Docker 构建成功" "$build_log" && echo "成功" || echo "失败")
- 镜像标签: $IMAGE_TAG
- 构建日志: docker-build.log

### 🚀 容器测试
- 容器启动: $([ "${ci_health_success:-false}" = "true" ] && echo "成功" || echo "失败")
- CI 健康检查: $([ "${ci_health_success:-false}" = "true" ] && echo "成功" || echo "失败")
- 标准健康检查: $([ "${standard_health_success:-false}" = "true" ] && echo "成功" || echo "失败")

### 📊 环境信息
- GitHub SHA: $GITHUB_SHA
- 构建时间: $(date)
- 平台: linux/amd64

## 🎯 问题分析

### 如果构建成功但 GitHub Actions 失败
可能的原因:
1. **网络问题**: GitHub Actions 环境网络限制
2. **资源限制**: GitHub Actions 资源不足
3. **权限问题**: Container Registry 推送权限
4. **环境差异**: 本地环境与 GitHub Actions 环境差异

### 如果本地模拟也失败
需要检查:
1. Dockerfile.github 语法
2. 依赖版本兼容性
3. 文件路径问题
4. 环境变量配置

## 💡 修复建议

### 如果是网络问题
- 增加重试机制
- 使用更稳定的基础镜像
- 优化依赖安装

### 如果是资源问题
- 减少构建步骤
- 使用多阶段构建
- 优化镜像大小

### 如果是权限问题
- 检查 GITHUB_TOKEN 权限
- 验证 Container Registry 设置

## 🚀 下一步行动

基于模拟结果提供具体的修复步骤。

EOF

# 清理临时文件
rm -f /tmp/*-health-sim.json

echo -e "${GREEN}✅ GitHub Actions 构建模拟完成！${NC}"
echo -e "${BLUE}📄 模拟报告: github-actions-simulation/simulation-report.md${NC}"
echo -e "${YELLOW}📁 详细日志保存在: github-actions-simulation/${NC}"

# 显示关键结果
echo -e "\n${CYAN}🎯 模拟结果总结:${NC}"

if [ "${ci_health_success:-false}" = "true" ] && [ "${standard_health_success:-false}" = "true" ]; then
    echo -e "${GREEN}✅ 本地模拟完全成功${NC}"
    echo -e "${YELLOW}⚠️  如果 GitHub Actions 仍然失败，可能是远程环境问题${NC}"
    echo -e "${BLUE}💡 建议检查 GitHub Actions 日志中的具体错误信息${NC}"
else
    echo -e "${RED}❌ 本地模拟发现问题${NC}"
    echo -e "${BLUE}💡 需要先解决本地问题，然后再推送到远程${NC}"
fi

echo -e "\n${PURPLE}🔍 请查看详细日志文件以获取更多信息${NC}"
