#!/bin/bash
# 🔍 CI/CD 状态检查脚本
# 帮助监控 GitHub Actions 工作流状态

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
COMMIT_SHA="46ac117"

echo -e "${BLUE}🔍 CI/CD 状态检查器${NC}"
echo "=================================="
echo -e "${PURPLE}仓库: ${REPO}${NC}"
echo -e "${PURPLE}提交: ${COMMIT_SHA}${NC}"
echo ""

# 检查最新提交
echo -e "${BLUE}📋 最新提交信息:${NC}"
git log --oneline -1
echo ""

# 显示 GitHub Actions 链接
echo -e "${BLUE}🔗 GitHub Actions 链接:${NC}"
echo "https://github.com/${REPO}/actions"
echo ""

# 显示具体工作流链接
echo -e "${BLUE}📊 当前工作流状态:${NC}"
echo "https://github.com/${REPO}/actions/runs"
echo ""

# 检查本地 Docker 构建（如果 Docker 可用）
if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    echo -e "${BLUE}🐳 本地 Docker 测试:${NC}"
    echo "运行以下命令进行本地验证:"
    echo -e "${GREEN}./quick-docker-test.sh${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Docker 不可用，无法进行本地测试${NC}"
    echo ""
fi

# 显示预期结果
echo -e "${BLUE}✅ 预期成功指标:${NC}"
echo "1. Code Quality Checks - 应该通过"
echo "2. Security Scanning - 应该通过"
echo "3. Testing Suite - 应该通过"
echo "4. Docker Build & Test - 🎯 这是关键步骤"
echo "5. Dev Compose Smoke - 应该通过"
echo ""

# 显示故障排查信息
echo -e "${BLUE}🔧 如果仍然失败:${NC}"
echo "1. 查看详细日志: 点击失败的 job"
echo "2. 使用备用方案: 切换到 Dockerfile.minimal"
echo "3. 查看故障排查指南: CI_CD_TROUBLESHOOTING.md"
echo ""

# 备用方案命令
echo -e "${BLUE}🚨 备用方案 (如果主构建失败):${NC}"
echo -e "${YELLOW}mv Dockerfile Dockerfile.full${NC}"
echo -e "${YELLOW}mv Dockerfile.minimal Dockerfile${NC}"
echo -e "${YELLOW}git add . && git commit -m \"fix: use minimal Dockerfile for CI stability\"${NC}"
echo -e "${YELLOW}git push origin main${NC}"
echo ""

# 实时状态检查提示
echo -e "${GREEN}🎯 下一步:${NC}"
echo "1. 打开浏览器查看 GitHub Actions 页面"
echo "2. 等待工作流完成 (通常需要 5-10 分钟)"
echo "3. 如果 Docker Build & Test 步骤通过，问题就解决了！"
echo ""

echo -e "${PURPLE}⏰ 监控提示: 每 2-3 分钟刷新一次 GitHub Actions 页面${NC}"
