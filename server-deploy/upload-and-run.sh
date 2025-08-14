#!/bin/bash
# 本地执行：上传文件到服务器并运行配置

echo "🚀 准备上传配置文件到服务器并执行..."
echo "======================================================="

# 检查必需文件
if [ ! -f ~/.ssh/Xp13408529631.pem ]; then
    echo "❌ 错误: 找不到私钥文件 ~/.ssh/Xp13408529631.pem"
    exit 1
fi

# 检查部署文件
if [ ! -f "remote-setup.sh" ]; then
    echo "❌ 错误: 找不到 remote-setup.sh 文件"
    exit 1
fi

echo "📤 上传配置文件到服务器..."
scp -i ~/.ssh/Xp13408529631.pem -o StrictHostKeyChecking=no \
    remote-setup.sh nginx-app.conf infrastructure-only.sh verify.sh \
    ubuntu@3.35.106.116:~/

echo "🔧 在服务器上执行配置..."
ssh -i ~/.ssh/Xp13408529631.pem -o StrictHostKeyChecking=no ubuntu@3.35.106.116 "
    echo '开始服务器配置...'
    chmod +x ~/remote-setup.sh
    bash ~/remote-setup.sh
"

echo ""
echo "✅ 服务器配置完成！"
echo "======================================================="
echo "📋 接下来你可以："
echo "  1. 推送代码到 GitHub"
echo "  2. CI/CD 会自动部署到服务器"
echo "  3. 测试 GitHub Webhook: http://3.35.106.116/github_webhook"
echo "" 