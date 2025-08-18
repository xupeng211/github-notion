#!/bin/bash
# 🔍 快速构建测试
# 快速诊断 GitHub Actions 构建问题

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 快速构建测试...${NC}"

# 1. 检查 Dockerfile.github
echo -e "${BLUE}1. 检查 Dockerfile.github...${NC}"
if [ -f "Dockerfile.github" ]; then
    echo "✅ Dockerfile.github 存在"
else
    echo "❌ Dockerfile.github 不存在"
    exit 1
fi

# 2. 快速构建测试
echo -e "${BLUE}2. 快速构建测试...${NC}"

image_name="quick-test:$(date +%s)"
echo "构建镜像: $image_name"

if timeout 300 docker build -f Dockerfile.github -t "$image_name" . 2>&1 | tee build-test.log; then
    echo -e "${GREEN}✅ 构建成功${NC}"
    
    # 3. 快速容器测试
    echo -e "${BLUE}3. 快速容器测试...${NC}"
    
    container_name="quick-test-$(date +%s)"
    
    if docker run -d --name "$container_name" \
        -p 8093:8000 \
        -e ENVIRONMENT=ci \
        -e GITHUB_TOKEN=placeholder \
        -e GITHUB_WEBHOOK_SECRET=placeholder \
        -e NOTION_TOKEN=placeholder \
        -e NOTION_DATABASE_ID=placeholder \
        -e DEADLETTER_REPLAY_TOKEN=placeholder \
        "$image_name"; then
        
        echo "✅ 容器启动成功"
        
        # 等待启动
        sleep 15
        
        # 检查容器状态
        if docker ps | grep -q "$container_name"; then
            echo "✅ 容器正在运行"
            
            # 快速健康检查
            echo -e "${BLUE}4. 快速健康检查...${NC}"
            
            if curl -f -m 10 http://localhost:8093/health/ci 2>/dev/null; then
                echo -e "${GREEN}✅ CI 健康检查成功${NC}"
                health_success=true
            else
                echo -e "${RED}❌ CI 健康检查失败${NC}"
                health_success=false
            fi
            
            # 获取容器日志
            echo -e "${BLUE}5. 容器日志 (最后 10 行):${NC}"
            docker logs --tail 10 "$container_name"
            
        else
            echo "❌ 容器已停止"
            docker logs "$container_name" 2>/dev/null || true
            health_success=false
        fi
        
        # 清理容器
        docker stop "$container_name" 2>/dev/null || true
        docker rm "$container_name" 2>/dev/null || true
        
    else
        echo "❌ 容器启动失败"
        health_success=false
    fi
    
    # 清理镜像
    docker rmi "$image_name" 2>/dev/null || true
    
else
    echo -e "${RED}❌ 构建失败${NC}"
    echo -e "${YELLOW}构建错误 (最后 20 行):${NC}"
    tail -20 build-test.log
    health_success=false
fi

# 6. 检查工作流配置问题
echo -e "${BLUE}6. 检查工作流配置...${NC}"

# 检查是否有多个工作流会被触发
push_workflows=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ] && grep -q "push:" "$workflow"; then
        push_workflows+=("$(basename "$workflow")")
    fi
done

echo "会被 push 触发的工作流: ${#push_workflows[@]} 个"
printf '%s\n' "${push_workflows[@]}"

if [ ${#push_workflows[@]} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  发现多个工作流会被触发，这可能导致冲突${NC}"
    
    # 检查 optimized-build.yml 是否还会被自动触发
    if grep -q "push:" .github/workflows/optimized-build.yml 2>/dev/null; then
        echo -e "${RED}❌ optimized-build.yml 仍然配置了 push 触发${NC}"
        echo "需要修复 optimized-build.yml 配置"
        workflow_conflict=true
    else
        echo "✅ optimized-build.yml 已配置为手动触发"
        workflow_conflict=false
    fi
else
    echo "✅ 只有 1 个工作流会被触发"
    workflow_conflict=false
fi

# 7. 总结
echo -e "\n${CYAN}📊 快速诊断结果:${NC}"

if [ "${health_success:-false}" = "true" ]; then
    echo -e "${GREEN}✅ 本地构建和健康检查成功${NC}"
else
    echo -e "${RED}❌ 本地构建或健康检查失败${NC}"
fi

if [ "${workflow_conflict:-false}" = "true" ]; then
    echo -e "${RED}❌ 发现工作流配置冲突${NC}"
else
    echo -e "${GREEN}✅ 工作流配置正常${NC}"
fi

echo -e "\n${BLUE}💡 建议:${NC}"

if [ "${health_success:-false}" = "true" ] && [ "${workflow_conflict:-false}" = "false" ]; then
    echo -e "${GREEN}本地测试完全正常，如果 GitHub Actions 仍然失败:${NC}"
    echo "1. 检查 GitHub Actions 日志中的具体错误"
    echo "2. 可能是网络或资源限制问题"
    echo "3. 检查 GitHub Container Registry 权限"
elif [ "${workflow_conflict:-false}" = "true" ]; then
    echo -e "${YELLOW}需要修复工作流冲突:${NC}"
    echo "1. 确保 optimized-build.yml 只能手动触发"
    echo "2. 移除多余的 push 触发配置"
else
    echo -e "${RED}需要修复本地构建问题:${NC}"
    echo "1. 检查 build-test.log 中的错误信息"
    echo "2. 修复 Dockerfile 或依赖问题"
fi

# 清理
rm -f build-test.log

echo -e "\n${CYAN}🔍 快速诊断完成${NC}"
