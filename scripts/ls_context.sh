#!/usr/bin/env bash
# 🔍 Docker构建上下文内容清单脚本
# 使用tar模拟.dockerignore打包，输出前200行内容

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Docker构建上下文内容清单${NC}"
echo "=================================================="

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 检查.dockerignore文件
if [[ ! -f .dockerignore ]]; then
    echo -e "${RED}❌ .dockerignore文件不存在${NC}"
    exit 1
fi

echo -e "${BLUE}📋 处理.dockerignore规则...${NC}"

# 读取.dockerignore并构建exclude数组
EXCLUDES=()
while IFS= read -r line; do
    # 跳过空行和注释
    [ -z "$line" ] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    
    # 移除前后空格
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -z "$line" ] && continue
    
    # 添加到exclude数组
    EXCLUDES+=("--exclude=$line")
done < .dockerignore

echo "生成的exclude规则数量: ${#EXCLUDES[@]}"

echo -e "\n${BLUE}🐳 模拟Docker构建上下文打包...${NC}"

# 使用tar模拟Docker构建上下文
if tar -cz "${EXCLUDES[@]}" . 2>/dev/null | tar -tz 2>/dev/null | head -n 200; then
    echo -e "\n${GREEN}✅ 构建上下文内容清单生成完成${NC}"
else
    echo -e "\n${RED}❌ 构建上下文清单生成失败${NC}"
    exit 1
fi

echo -e "\n${BLUE}🔍 关键目录检查:${NC}"

# 检查关键目录是否存在
CRITICAL_PATHS=(
    "app/"
    "infra/"
    "requirements.txt"
    "scripts/"
)

echo "检查关键路径是否包含在构建上下文中:"

for path in "${CRITICAL_PATHS[@]}"; do
    if tar -cz "${EXCLUDES[@]}" . 2>/dev/null | tar -tz 2>/dev/null | grep -q "^${path}"; then
        echo -e "  ✅ ${path}"
    else
        echo -e "  ❌ ${path} - 可能被过度忽略"
    fi
done
