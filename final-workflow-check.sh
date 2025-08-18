#!/bin/bash
# 🔍 最终工作流检查
# 精确检查工作流触发条件

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 最终工作流检查...${NC}"

# 检查每个工作流的触发条件
echo -e "${BLUE}检查工作流触发条件...${NC}"

push_workflows=()
manual_workflows=()

for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        
        # 检查 on: 部分的 push 触发
        if awk '/^on:/{flag=1; next} /^[a-zA-Z]/ && flag{exit} flag && /push:/{print; exit}' "$workflow" | grep -q "push:"; then
            push_workflows+=("$workflow_name")
            echo "🔴 $workflow_name: 配置了 push 触发"
        elif grep -q "workflow_dispatch:" "$workflow"; then
            manual_workflows+=("$workflow_name")
            echo "🟡 $workflow_name: 只能手动触发"
        else
            echo "⚪ $workflow_name: 其他触发条件"
        fi
    fi
done

echo -e "\n${CYAN}📊 工作流触发总结:${NC}"
echo "会被 push 触发的工作流: ${#push_workflows[@]} 个"
if [ ${#push_workflows[@]} -gt 0 ]; then
    printf '  - %s\n' "${push_workflows[@]}"
fi

echo "只能手动触发的工作流: ${#manual_workflows[@]} 个"
if [ ${#manual_workflows[@]} -gt 0 ]; then
    printf '  - %s\n' "${manual_workflows[@]}"
fi

# 判断是否有冲突
if [ ${#push_workflows[@]} -eq 1 ]; then
    echo -e "\n${GREEN}✅ 工作流配置正确：只有 1 个工作流会被 push 触发${NC}"
    workflow_ok=true
elif [ ${#push_workflows[@]} -eq 0 ]; then
    echo -e "\n${YELLOW}⚠️  没有工作流会被 push 触发${NC}"
    workflow_ok=false
else
    echo -e "\n${RED}❌ 工作流冲突：${#push_workflows[@]} 个工作流会被 push 触发${NC}"
    workflow_ok=false
fi

# 快速构建测试
echo -e "\n${BLUE}快速构建验证...${NC}"

image_name="final-test:$(date +%s)"
if timeout 120 docker build -f Dockerfile.github -t "$image_name" . > /dev/null 2>&1; then
    echo "✅ Docker 构建成功"
    docker rmi "$image_name" 2>/dev/null || true
    build_ok=true
else
    echo "❌ Docker 构建失败"
    build_ok=false
fi

# 最终结论
echo -e "\n${CYAN}🎯 最终检查结果:${NC}"

if [ "$workflow_ok" = true ] && [ "$build_ok" = true ]; then
    echo -e "${GREEN}🎉 所有检查通过！CI/CD 应该能够成功运行${NC}"
    echo -e "${GREEN}✅ 工作流配置正确${NC}"
    echo -e "${GREEN}✅ 本地构建成功${NC}"
    echo -e "\n${BLUE}💡 如果 GitHub Actions 仍然失败，可能的原因:${NC}"
    echo "1. 网络问题或资源限制"
    echo "2. GitHub Container Registry 权限问题"
    echo "3. 远程环境差异"
    exit 0
elif [ "$workflow_ok" = false ]; then
    echo -e "${RED}❌ 工作流配置有问题${NC}"
    echo -e "${YELLOW}💡 需要修复工作流触发条件${NC}"
    exit 1
else
    echo -e "${RED}❌ 本地构建有问题${NC}"
    echo -e "${YELLOW}💡 需要修复 Dockerfile 或依赖问题${NC}"
    exit 1
fi
