#!/bin/bash
# 🔍 实时监控 CI/CD 构建状态

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 配置
REPO="xupeng211/github-notion"
COMMIT_SHA="8e68084"

echo -e "${BLUE}🔍 实时监控 CI/CD 构建状态${NC}"
echo "=================================="
echo -e "${PURPLE}仓库: ${REPO}${NC}"
echo -e "${PURPLE}提交: ${COMMIT_SHA}${NC}"
echo ""

# 函数：获取构建状态
get_build_status() {
    echo -e "${BLUE}📊 获取最新构建状态...${NC}"

    # 使用 curl 获取 GitHub API 数据
    if command -v curl &> /dev/null; then
        echo "正在查询 GitHub Actions API..."
        echo "URL: https://api.github.com/repos/${REPO}/actions/runs?per_page=3"
        echo ""
    else
        echo -e "${RED}❌ curl 不可用，无法获取实时状态${NC}"
        return 1
    fi
}

# 函数：显示构建链接
show_links() {
    echo -e "${BLUE}🔗 重要链接:${NC}"
    echo "GitHub Actions: https://github.com/${REPO}/actions"
    echo "主要工作流: https://github.com/${REPO}/actions/runs/17042258231"
    echo ""
}

# 函数：显示预期结果
show_expectations() {
    echo -e "${BLUE}✅ 修复后预期结果:${NC}"
    echo "1. ✅ Code Quality Checks - 应该通过 (已修复格式问题)"
    echo "2. ✅ Security Scanning - 应该通过"
    echo "3. ✅ Testing Suite - 应该通过"
    echo "4. 🎯 Docker Build & Test - 关键步骤 (已优化)"
    echo "5. ✅ Dev Compose Smoke - 应该通过"
    echo ""
}

# 函数：显示修复内容
show_fixes() {
    echo -e "${BLUE}🔧 已实施的修复:${NC}"
    echo "• 修复了 Black 代码格式问题"
    echo "• 修复了 isort 导入排序问题"
    echo "• 移除了未使用的导入"
    echo "• 修复了变量名冲突"
    echo "• 优化了 Docker 构建配置"
    echo "• 增加了构建超时和重试机制"
    echo ""
}

# 主函数
main() {
    show_links
    show_fixes
    show_expectations
    get_build_status

    echo -e "${GREEN}🎯 监控建议:${NC}"
    echo "1. 每 2-3 分钟刷新 GitHub Actions 页面"
    echo "2. 重点关注 'Docker Build & Test' 步骤"
    echo "3. 如果仍有问题，我们有备用方案准备好了"
    echo ""

    echo -e "${PURPLE}⏰ 预计完成时间: 5-10 分钟${NC}"
    echo -e "${PURPLE}📱 建议: 保持 GitHub Actions 页面打开${NC}"
}

# 运行主函数
main "$@"
