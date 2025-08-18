#!/bin/bash
# 🔍 检查工作流触发条件
# 分析为什么 CI/CD 没有被触发

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 检查工作流触发条件...${NC}"

# 1. 检查最近的提交
echo -e "${BLUE}1. 检查最近的提交...${NC}"
echo "最近的 5 个提交:"
git log --oneline -5

echo -e "\n最新提交的详细信息:"
git show --stat HEAD

# 2. 检查每个工作流的触发条件
echo -e "\n${BLUE}2. 分析工作流触发条件...${NC}"

for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        echo -e "\n${PURPLE}=== $workflow_name ===${NC}"
        
        # 提取 on: 部分
        echo "触发条件:"
        awk '/^on:/{flag=1} flag{print} /^[a-zA-Z][^:]*:/ && flag && !/^on:/{if(prev_line !~ /^[[:space:]]/){exit}} {prev_line=$0}' "$workflow" | head -20
        
        # 检查是否有 push 触发
        if awk '/^on:/{flag=1; next} /^[a-zA-Z]/ && flag && !/^[[:space:]]/{exit} flag && /push:/{found=1} END{exit !found}' "$workflow"; then
            echo -e "${GREEN}✅ 配置了 push 触发${NC}"
            
            # 检查分支限制
            if awk '/^on:/{flag=1} flag && /push:/{push_flag=1} push_flag && /branches:/{branch_flag=1} branch_flag && /main|master/{found=1} /^[a-zA-Z]/ && flag && !/^[[:space:]]/ && !/^on:/{exit} END{exit !found}' "$workflow"; then
                echo -e "${GREEN}  ✅ 会在 main 分支触发${NC}"
            else
                echo -e "${YELLOW}  ⚠️  可能不会在 main 分支触发${NC}"
            fi
            
            # 检查路径限制
            if awk '/^on:/{flag=1} flag && /push:/{push_flag=1} push_flag && /paths:/{path_flag=1} path_flag && /^[[:space:]]*-/{print "  路径限制: " $0} /^[a-zA-Z]/ && flag && !/^[[:space:]]/ && !/^on:/{exit}' "$workflow" | grep -q "路径限制"; then
                echo -e "${YELLOW}  ⚠️  有路径限制:${NC}"
                awk '/^on:/{flag=1} flag && /push:/{push_flag=1} push_flag && /paths:/{path_flag=1} path_flag && /^[[:space:]]*-/{print "    " $0} /^[a-zA-Z]/ && flag && !/^[[:space:]]/ && !/^on:/{exit}' "$workflow"
            else
                echo -e "${GREEN}  ✅ 无路径限制${NC}"
            fi
        else
            echo -e "${RED}❌ 未配置 push 触发${NC}"
        fi
        
        # 检查是否有 workflow_dispatch
        if grep -q "workflow_dispatch:" "$workflow"; then
            echo -e "${BLUE}  ℹ️  支持手动触发${NC}"
        fi
    fi
done

# 3. 检查最新提交是否应该触发工作流
echo -e "\n${BLUE}3. 检查最新提交是否应该触发工作流...${NC}"

# 获取最新提交修改的文件
echo "最新提交修改的文件:"
git diff --name-only HEAD~1 HEAD

echo -e "\n分析触发条件匹配:"

for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        
        # 检查是否有 push 触发
        if awk '/^on:/{flag=1; next} /^[a-zA-Z]/ && flag && !/^[[:space:]]/{exit} flag && /push:/{found=1} END{exit !found}' "$workflow"; then
            echo -e "\n${PURPLE}$workflow_name:${NC}"
            
            # 检查路径限制
            if awk '/^on:/{flag=1} flag && /push:/{push_flag=1} push_flag && /paths:/{found=1} END{exit !found}' "$workflow"; then
                echo "  有路径限制，检查是否匹配..."
                
                # 提取路径模式
                paths=$(awk '/^on:/{flag=1} flag && /push:/{push_flag=1} push_flag && /paths:/{path_flag=1} path_flag && /^[[:space:]]*-/{gsub(/^[[:space:]]*-[[:space:]]*/, ""); gsub(/['\''"]/, ""); print} /^[a-zA-Z]/ && flag && !/^[[:space:]]/ && !/^on:/{exit}' "$workflow")
                
                # 检查修改的文件是否匹配路径模式
                changed_files=$(git diff --name-only HEAD~1 HEAD)
                match_found=false
                
                while IFS= read -r pattern; do
                    if [ -n "$pattern" ]; then
                        echo "    检查模式: $pattern"
                        while IFS= read -r file; do
                            if [[ "$file" == $pattern ]]; then
                                echo "      ✅ 匹配文件: $file"
                                match_found=true
                            fi
                        done <<< "$changed_files"
                    fi
                done <<< "$paths"
                
                if [ "$match_found" = true ]; then
                    echo -e "  ${GREEN}✅ 应该触发此工作流${NC}"
                else
                    echo -e "  ${YELLOW}❌ 不应该触发此工作流（路径不匹配）${NC}"
                fi
            else
                echo -e "  ${GREEN}✅ 无路径限制，应该触发${NC}"
            fi
        fi
    fi
done

# 4. 检查 GitHub Actions 状态
echo -e "\n${BLUE}4. 检查可能的问题...${NC}"

# 检查工作流文件语法
echo "检查工作流文件语法:"
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            echo "  ✅ $workflow_name 语法正确"
        else
            echo -e "  ${RED}❌ $workflow_name 语法错误${NC}"
            python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>&1 | head -5
        fi
    fi
done

# 检查是否有多个工作流冲突
echo -e "\n检查工作流冲突:"
push_workflows=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ] && awk '/^on:/{flag=1; next} /^[a-zA-Z]/ && flag && !/^[[:space:]]/{exit} flag && /push:/{found=1} END{exit !found}' "$workflow"; then
        push_workflows+=("$(basename "$workflow")")
    fi
done

echo "会被 push 触发的工作流: ${#push_workflows[@]} 个"
if [ ${#push_workflows[@]} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  发现多个工作流会被触发，可能导致冲突:${NC}"
    printf '  - %s\n' "${push_workflows[@]}"
else
    echo -e "${GREEN}✅ 工作流配置正常${NC}"
fi

# 5. 提供解决建议
echo -e "\n${CYAN}💡 可能的原因和解决方案:${NC}"

if [ ${#push_workflows[@]} -eq 0 ]; then
    echo -e "${RED}❌ 没有工作流会被 push 触发${NC}"
    echo "解决方案:"
    echo "1. 检查工作流文件的 on: push: 配置"
    echo "2. 确保至少有一个工作流配置了 push 触发"
elif [ ${#push_workflows[@]} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  多个工作流可能导致冲突${NC}"
    echo "解决方案:"
    echo "1. 只保留一个主要的 CI/CD 工作流"
    echo "2. 将其他工作流改为手动触发"
else
    echo -e "${GREEN}✅ 工作流配置看起来正常${NC}"
    echo "如果仍然没有触发，可能的原因:"
    echo "1. 路径限制：修改的文件不在触发路径中"
    echo "2. 分支限制：不在指定分支上"
    echo "3. GitHub Actions 服务问题"
    echo "4. 仓库权限问题"
    echo "5. 工作流被禁用"
fi

echo -e "\n${BLUE}建议检查:${NC}"
echo "1. 访问 GitHub 仓库的 Actions 页面"
echo "2. 检查是否有工作流运行记录"
echo "3. 查看是否有错误信息"
echo "4. 确认 GitHub Actions 是否启用"

echo -e "\n${CYAN}🔍 检查完成${NC}"
