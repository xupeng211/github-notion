#!/bin/bash
# 生产环境安全验证脚本
# 确保所有密钥都已正确配置，没有使用默认值

set -e

echo "🔐 开始生产环境安全验证..."
echo "======================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VALIDATION_PASSED=true

# 验证函数
validate_secret() {
    local var_name="$1"
    local min_length="${2:-16}"
    local var_value="${!var_name}"

    if [ -z "$var_value" ]; then
        echo -e "  ❌ ${RED}$var_name 未设置${NC}"
        VALIDATION_PASSED=false
        return 1
    fi

    # 检查是否为占位符值
    case "$var_value" in
        *"your_"*|*"changeme"*|*"default"*|*"secret_here"*|*"token_here"*)
            echo -e "  ❌ ${RED}$var_name 使用了占位符值${NC}"
            VALIDATION_PASSED=false
            return 1
            ;;
        "s"|"k"|"ci-secret"|"test"|"admin123"|"default-token-123")
            echo -e "  ❌ ${RED}$var_name 使用了测试/默认值${NC}"
            VALIDATION_PASSED=false
            return 1
            ;;
    esac

    # 检查长度
    if [ ${#var_value} -lt $min_length ]; then
        echo -e "  ❌ ${RED}$var_name 长度不足 (< $min_length)${NC}"
        VALIDATION_PASSED=false
        return 1
    fi

    echo -e "  ✅ ${GREEN}$var_name 已正确配置${NC}"
    return 0
}

# 验证环境
ENVIRONMENT=${ENVIRONMENT:-development}
echo -e "${BLUE}当前环境: $ENVIRONMENT${NC}\n"

# 核心密钥验证
echo "📋 验证核心密钥:"
validate_secret "GITHUB_TOKEN" 40
validate_secret "NOTION_TOKEN" 43
validate_secret "NOTION_DATABASE_ID" 32

# Webhook 密钥验证
echo -e "\n📋 验证 Webhook 密钥:"
validate_secret "GITHUB_WEBHOOK_SECRET" 20
validate_secret "GITEE_WEBHOOK_SECRET" 20
validate_secret "NOTION_WEBHOOK_SECRET" 20

# 管理令牌验证
echo -e "\n📋 验证管理令牌:"
if [ "$ENVIRONMENT" = "production" ]; then
    validate_secret "DEADLETTER_REPLAY_TOKEN" 32
    validate_secret "GRAFANA_PASSWORD" 12
    validate_secret "GRAFANA_SECRET_KEY" 32
else
    echo -e "  ℹ️ ${YELLOW}非生产环境，跳过管理令牌检查${NC}"
fi

# 检查弱密钥模式
echo -e "\n📋 检查代码中的硬编码密钥:"
if grep -r "ghp_\|secret_\|token.*=" app/ 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__"; then
    echo -e "  ❌ ${RED}发现可能的硬编码密钥${NC}"
    VALIDATION_PASSED=false
else
    echo -e "  ✅ ${GREEN}未发现硬编码密钥${NC}"
fi

# 最终结果
echo -e "\n======================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "🎉 ${GREEN}安全验证通过！所有密钥配置正确${NC}"
    echo -e "✅ 可以安全部署到 $ENVIRONMENT 环境"
    exit 0
else
    echo -e "💥 ${RED}安全验证失败！${NC}"
    echo -e "❌ 请修复上述问题后重新验证"
    echo -e "\n💡 修复建议:"
    echo -e "   1. 使用 openssl rand -hex 32 生成强密钥"
    echo -e "   2. 确保所有密钥长度足够且随机"
    echo -e "   3. 绝不在代码中硬编码密钥"
    exit 1
fi
