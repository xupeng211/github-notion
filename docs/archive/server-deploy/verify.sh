#!/bin/bash
# 一键验证脚本 - GitHub-Notion 同步系统
# 检查所有关键环节是否正常工作

set -e

echo "🧪 GitHub-Notion 同步系统验证检查"
echo "======================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果统计
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# 检查函数
check_pass() {
    echo -e "  ✅ ${GREEN}$1${NC}"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "  ❌ ${RED}$1${NC}"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "  ⚠️  ${YELLOW}$1${NC}"
    ((WARN_COUNT++))
}

# 1. 检查端口监听
echo "🔍 检查端口监听状态..."
if sudo ss -tlnp | grep -q ':80.*nginx'; then
    check_pass "端口 80 由 Nginx 监听"
else
    check_fail "端口 80 未被 Nginx 监听"
fi

if sudo ss -tlnp | grep -q ':8000'; then
    check_pass "端口 8000 有进程监听"
else
    check_fail "端口 8000 无进程监听"
fi

# 2. 检查 Nginx 配置
echo ""
echo "⚙️ 检查 Nginx 配置..."
if [ -f "/etc/nginx/sites-available/app.conf" ]; then
    check_pass "Nginx 配置文件存在"
else
    check_fail "Nginx 配置文件不存在"
fi

if [ -L "/etc/nginx/sites-enabled/app.conf" ]; then
    check_pass "站点配置已启用"
else
    check_fail "站点配置未启用"
fi

if sudo nginx -t &>/dev/null; then
    check_pass "Nginx 配置语法正确"
else
    check_fail "Nginx 配置语法错误"
fi

# 3. 检查必需目录
echo ""
echo "📁 检查项目目录..."
if [ -d "data" ]; then
    check_pass "data/ 目录存在"
    if [ -w "data" ]; then
        check_pass "data/ 目录可写"
    else
        check_fail "data/ 目录不可写"
    fi
else
    check_fail "data/ 目录不存在"
fi

if [ -d "logs" ]; then
    check_pass "logs/ 目录存在"
else
    check_warn "logs/ 目录不存在（非必需）"
fi

# 4. 检查环境变量文件
echo ""
echo "🔐 检查环境配置..."
if [ -f ".env" ]; then
    check_pass ".env 文件存在"

    if grep -q "GITHUB_TOKEN=" .env && grep -q "NOTION_TOKEN=" .env; then
        check_pass "关键环境变量已配置"
    else
        check_fail "缺少关键环境变量"
    fi
else
    check_fail ".env 文件不存在"
fi

# 5. 测试本地 8000 端口连接
echo ""
echo "🔗 测试本地服务连接..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health | grep -q "200"; then
    check_pass "本地 8000 端口 /health 返回 200"
else
    check_fail "本地 8000 端口 /health 连接失败"
fi

# 6. 测试 80 端口反向代理
echo ""
echo "🌐 测试反向代理连接..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health | grep -q "200"; then
    check_pass "80 端口 /health 反向代理正常"
else
    check_fail "80 端口 /health 反向代理失败"
fi

if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/github_webhook -X POST | grep -q "200\|405"; then
    check_pass "80 端口 /github_webhook 端点可访问"
else
    check_fail "80 端口 /github_webhook 端点不可访问"
fi

# 7. 测试外网访问（如果可能）
echo ""
echo "🌍 测试外网访问..."
EXTERNAL_IP="3.35.106.116"
if timeout 10 curl -s -o /dev/null -w "%{http_code}" http://$EXTERNAL_IP/health | grep -q "200"; then
    check_pass "外网 /health 访问正常"
else
    check_warn "外网 /health 访问失败（可能是防火墙或网络问题）"
fi

if timeout 10 curl -s -o /dev/null -w "%{http_code}" http://$EXTERNAL_IP/github_webhook -X POST | grep -q "200\|405"; then
    check_pass "外网 /github_webhook 访问正常"
else
    check_warn "外网 /github_webhook 访问失败（可能是防火墙或网络问题）"
fi

# 8. 检查服务状态
echo ""
echo "🔄 检查服务状态..."
if systemctl is-active nginx >/dev/null 2>&1; then
    check_pass "Nginx 服务运行中"
else
    check_fail "Nginx 服务未运行"
fi

# 9. 检查日志文件
echo ""
echo "📋 检查日志配置..."
if [ -f "/var/log/nginx/github_notion_access.log" ]; then
    check_pass "Nginx 访问日志配置正确"
else
    check_warn "Nginx 访问日志文件不存在"
fi

if [ -f "/var/log/nginx/github_notion_error.log" ]; then
    check_pass "Nginx 错误日志配置正确"
else
    check_warn "Nginx 错误日志文件不存在"
fi

# 10. 显示实用的测试命令
echo ""
echo "📋 手动测试命令："
echo "  # 本地健康检查"
echo "  curl -i http://127.0.0.1:8000/health"
echo ""
echo "  # 反向代理健康检查"
echo "  curl -i http://127.0.0.1/health"
echo ""
echo "  # 外网健康检查"
echo "  curl -i http://$EXTERNAL_IP/health"
echo ""
echo "  # GitHub Webhook 测试"
echo "  curl -i -X POST http://$EXTERNAL_IP/github_webhook -H 'Content-Type: application/json' -d '{\"zen\":\"test\"}'"
echo ""
echo "  # 查看 Nginx 日志"
echo "  sudo tail -f /var/log/nginx/github_notion_access.log"
echo "  sudo tail -f /var/log/nginx/github_notion_error.log"

# 11. 总结报告
echo ""
echo "======================================================="
echo "📊 验证结果总结："
echo -e "  ✅ 通过: ${GREEN}$PASS_COUNT${NC}"
echo -e "  ⚠️  警告: ${YELLOW}$WARN_COUNT${NC}"
echo -e "  ❌ 失败: ${RED}$FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "🎉 ${GREEN}所有关键检查通过！系统准备就绪！${NC}"
    echo ""
    echo "📋 GitHub Webhook 配置："
    echo "  URL: http://$EXTERNAL_IP/github_webhook"
    echo "  Content Type: application/json"
    echo "  Events: Issues, Issue comments"
    echo ""
    echo "🔍 在 GitHub Webhook 页面点击 'Redeliver' 后："
    echo "  Recent Deliveries 应显示 Response: 200 ✅"
    echo "  如果显示其他状态码，请检查应用程序日志"
else
    echo ""
    echo -e "⚠️  ${YELLOW}发现 $FAIL_COUNT 个问题，需要修复后再测试${NC}"
    exit 1
fi
