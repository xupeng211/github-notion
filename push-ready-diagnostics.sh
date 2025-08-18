#!/bin/bash
# 🚀 推送就绪诊断 - 专注于关键问题
# 只检测真正会导致远程构建失败的硬编码问题

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 推送就绪诊断...${NC}"

# 检测关键的硬编码问题
critical_issues=0

# 1. 检测关键配置文件中的硬编码 IP
echo -e "${BLUE}1. 检查关键配置文件中的硬编码 IP...${NC}"
critical_files=(
    "docker-compose.yml"
    "docker-compose.prod.yml"
    ".github/workflows/ci-build.yml"
    ".github/workflows/aws-deploy-robust.yml"
    ".github/workflows/optimized-build.yml"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "3\.35\.106\.116" "$file" && ! grep -q "\${" "$file"; then
            echo -e "${RED}❌ 发现关键硬编码 IP: $file${NC}"
            ((critical_issues++))
        fi
    fi
done

# 2. 检测关键配置文件中的硬编码端口
echo -e "${BLUE}2. 检查关键配置文件中的硬编码端口...${NC}"
for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        if grep -q ":8000" "$file" && ! grep -q "\${" "$file" && ! grep -q "APP_PORT" "$file"; then
            echo -e "${RED}❌ 发现关键硬编码端口: $file${NC}"
            ((critical_issues++))
        fi
    fi
done

# 3. 检查 Python 语法
echo -e "${BLUE}3. 检查 Python 语法...${NC}"
syntax_errors=0
for py_file in $(find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | head -10); do
    if ! python3 -m py_compile "$py_file" 2>/dev/null; then
        echo -e "${RED}❌ 语法错误: $py_file${NC}"
        ((syntax_errors++))
        ((critical_issues++))
    fi
done

# 4. 检查关键文件存在性
echo -e "${BLUE}4. 检查关键文件...${NC}"
required_files=("requirements.txt" "app/server.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ 缺少关键文件: $file${NC}"
        ((critical_issues++))
    fi
done

# 5. 检查 YAML 语法
echo -e "${BLUE}5. 检查 YAML 语法...${NC}"
for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
    if [ -f "$workflow" ]; then
        if ! python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            echo -e "${RED}❌ YAML 语法错误: $(basename $workflow)${NC}"
            ((critical_issues++))
        fi
    fi
done

# 总结
echo ""
if [ "$critical_issues" -eq 0 ]; then
    echo -e "${GREEN}✅ 推送就绪检查通过！${NC}"
    echo -e "${GREEN}🚀 代码可以安全推送到远程仓库${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $critical_issues 个关键问题${NC}"
    echo -e "${YELLOW}💡 这些问题可能导致远程构建失败${NC}"
    exit 1
fi
