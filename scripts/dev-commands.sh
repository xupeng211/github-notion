#!/bin/bash
# 🛠️ 开发者便捷命令

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 智能提交命令
smart_commit() {
    echo -e "${BLUE}🧠 智能提交流程...${NC}"
    
    # 1. 自动修复
    echo -e "${PURPLE}1. 自动修复问题...${NC}"
    if [ -f "./auto-fix-build-issues.sh" ]; then
        ./auto-fix-build-issues.sh
    fi
    
    # 2. 添加所有文件
    echo -e "${PURPLE}2. 添加文件到暂存区...${NC}"
    git add .
    
    # 3. 提交
    if [ -n "$1" ]; then
        echo -e "${PURPLE}3. 提交更改...${NC}"
        git commit -m "$1"
    else
        echo -e "${YELLOW}请提供提交信息:${NC}"
        echo "用法: smart_commit \"你的提交信息\""
        return 1
    fi
    
    echo -e "${GREEN}✅ 智能提交完成！${NC}"
}

# 安全推送命令
safe_push() {
    echo -e "${BLUE}🛡️ 安全推送流程...${NC}"

    # 1. 运行推送就绪诊断
    echo -e "${PURPLE}1. 推送就绪检查...${NC}"
    if [ -f "./push-ready-diagnostics.sh" ]; then
        if ! ./push-ready-diagnostics.sh; then
            echo -e "${RED}❌ 推送就绪检查失败，推送被阻止${NC}"
            return 1
        fi
    elif [ -f "./comprehensive-build-diagnostics.sh" ]; then
        echo -e "${YELLOW}⚠️  使用完整诊断作为备选${NC}"
        if ! ./comprehensive-build-diagnostics.sh; then
            echo -e "${RED}❌ 诊断失败，推送被阻止${NC}"
            return 1
        fi
    fi
    
    # 2. 推送
    echo -e "${PURPLE}2. 推送到远程...${NC}"
    git push "$@"
    
    echo -e "${GREEN}✅ 安全推送完成！${NC}"
}

# 完整开发流程
dev_flow() {
    echo -e "${CYAN}🚀 完整开发流程...${NC}"
    
    if [ -z "$1" ]; then
        echo -e "${YELLOW}用法: dev_flow \"提交信息\"${NC}"
        return 1
    fi
    
    # 1. 智能提交
    smart_commit "$1"
    
    # 2. 安全推送
    safe_push
    
    echo -e "${GREEN}🎉 开发流程完成！${NC}"
    echo -e "${BLUE}💡 可以在 GitHub Actions 中查看构建结果${NC}"
}

# 快速修复命令
quick_fix() {
    echo -e "${BLUE}⚡ 快速修复...${NC}"
    
    # 代码格式化
    if command -v black >/dev/null 2>&1; then
        black . --quiet
    fi
    
    if command -v isort >/dev/null 2>&1; then
        isort . --quiet
    fi
    
    # 检测问题
    if [ -f "./fix-hardcoded-values.py" ]; then
        python3 fix-hardcoded-values.py
    fi
    
    echo -e "${GREEN}✅ 快速修复完成${NC}"
}

# 本地测试命令
local_test() {
    echo -e "${BLUE}🧪 本地测试...${NC}"

    if [ -f "./test-build-locally.sh" ]; then
        ./test-build-locally.sh
    else
        echo -e "${YELLOW}⚠️  本地测试脚本不存在${NC}"
    fi
}

# 安全测试命令
security_test() {
    echo -e "${BLUE}🔐 安全测试...${NC}"

    if [ -f "./run-security-tests.sh" ]; then
        ./run-security-tests.sh
    else
        echo -e "${YELLOW}⚠️  安全测试脚本不存在${NC}"
        echo "运行以下命令设置安全测试:"
        echo "  ./setup-priority-tests.sh"
    fi
}

# 核心业务逻辑测试命令
core_business_test() {
    echo -e "${BLUE}🟡 核心业务逻辑测试...${NC}"

    if [ -f "./run-core-business-tests.sh" ]; then
        ./run-core-business-tests.sh
    else
        echo -e "${YELLOW}⚠️  核心业务逻辑测试脚本不存在${NC}"
        echo "运行以下命令设置核心业务逻辑测试:"
        echo "  ./setup-priority-tests.sh"
    fi
}

# 导出函数
export -f smart_commit
export -f safe_push
export -f dev_flow
export -f quick_fix
export -f local_test
export -f security_test
export -f core_business_test

echo -e "${GREEN}🛠️ 开发者命令已加载！${NC}"
echo ""
echo -e "${BLUE}可用命令:${NC}"
echo -e "  ${PURPLE}smart_commit \"消息\"${NC} - 智能提交（自动修复 + 提交）"
echo -e "  ${PURPLE}safe_push${NC}           - 安全推送（诊断 + 推送）"
echo -e "  ${PURPLE}dev_flow \"消息\"${NC}     - 完整流程（修复 + 提交 + 推送）"
echo -e "  ${PURPLE}quick_fix${NC}           - 快速修复代码问题"
echo -e "  ${PURPLE}local_test${NC}          - 本地构建测试"
echo -e "  ${PURPLE}security_test${NC}       - 运行安全测试（30秒）"
echo -e "  ${PURPLE}core_business_test${NC}  - 运行核心业务逻辑测试（1分钟）"
echo ""
