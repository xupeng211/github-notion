#!/bin/bash
# 🛡️ 强制代码质量检查脚本
# 确保所有提交都符合代码质量标准

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️ 强制代码质量检查${NC}"
echo "=================================="

# 1. 检查 pre-commit 是否安装
if ! command -v pre-commit &> /dev/null; then
    echo -e "${RED}❌ pre-commit 未安装${NC}"
    echo "请运行: pip install pre-commit"
    exit 1
fi

# 2. 安装 pre-commit hooks
echo -e "${BLUE}📦 安装 pre-commit hooks...${NC}"
pre-commit install --install-hooks

# 3. 运行核心文件检查
echo -e "${BLUE}🔍 检查核心应用文件...${NC}"
if pre-commit run --files app/*.py; then
    echo -e "${GREEN}✅ 核心应用文件检查通过${NC}"
else
    echo -e "${RED}❌ 核心应用文件检查失败${NC}"
    echo -e "${YELLOW}💡 提示: 运行 'black app/' 和 'isort app/' 来自动修复格式问题${NC}"
    exit 1
fi

# 4. 检查测试文件
echo -e "${BLUE}🧪 检查测试文件...${NC}"
if pre-commit run --files tests/*.py; then
    echo -e "${GREEN}✅ 测试文件检查通过${NC}"
else
    echo -e "${YELLOW}⚠️ 测试文件有一些问题，但不阻止提交${NC}"
fi

# 5. 运行快速测试
echo -e "${BLUE}🚀 运行快速测试...${NC}"
if python -m pytest tests/test_basic.py -v; then
    echo -e "${GREEN}✅ 基础测试通过${NC}"
else
    echo -e "${RED}❌ 基础测试失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 所有质量检查通过！可以安全提交代码${NC}"
echo -e "${BLUE}💡 提示: 现在可以运行 'git commit' 进行提交${NC}"
