#!/bin/bash
# 🔍 检查环境变量配置

echo "🔍 检查环境变量配置..."

# 检查必需的环境变量
required_vars=(
    "AWS_SERVER"
    "APP_PORT"
    "APP_DIR"
    "SERVICE_NAME"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing_vars+=("$var")
    else
        echo "✅ $var = ${!var}"
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo ""
    echo "❌ 缺少以下环境变量:"
    printf '%s\n' "${missing_vars[@]}"
    echo ""
    echo "💡 请在 .env 文件中配置这些变量"
    exit 1
else
    echo ""
    echo "✅ 所有必需的环境变量都已配置"
fi
