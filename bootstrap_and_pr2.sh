#!/usr/bin/env bash
# 一键初始化 main 并推送 + 生成 PR 2/5 分支（reverse-proxy-https）并推送
# 用法：
#   bash bootstrap_and_pr2.sh https://gitee.com/xupeng_11/football-predictor.git

set -euo pipefail

REMOTE_URL="${1:-}"
if [[ -z "${REMOTE_URL}" ]]; then
  echo "用法：bash $0 <GITEE_REMOTE_URL>"
  echo "示例：bash $0 https://gitee.com/xupeng_11/football-predictor.git"
  exit 1
fi

echo "==> 0) 确认当前目录为项目根目录（应能看到你的代码与 docker-compose.yml 等）"
pwd

echo "==> 1) 初始化 Git 仓库（如未初始化）并绑定远程"
if [ ! -d ".git" ]; then
  git init
fi

# 绑定远程（已存在则跳过）
if git remote | grep -q '^origin$'; then
  echo "origin 已存在，跳过 remote add"
else
  git remote add origin "${REMOTE_URL}"
fi

# 确保 .gitignore 至少忽略关键项（不覆盖，只追加缺少的行）
touch .gitignore
for line in ".env" "data/" "backups/" "__pycache__/" "node_modules/"; do
  grep -qxF "$line" .gitignore || echo "$line" >> .gitignore
done

echo "==> 2) 推送当前项目到 main（首次）"
# 检查是否已有提交
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "已有本地提交，准备推送到 main"
else
  git add .
  git commit -m "chore: initial commit - base project setup"
fi
git branch -M main
git push -u origin main || {
  echo "⚠️ 推送 main 失败，请检查远程权限或网络"; exit 1;
}

echo "==> 3) 生成 PR 2/5（reverse-proxy-https）所需文件"
mkdir -p reverse-proxy infra

# Caddyfile（自动 HTTPS）
cat > reverse-proxy/Caddyfile <<'EOF'
{
	email {$EMAIL_FOR_SSL}
}

{$DOMAIN_NAME} {
	encode zstd gzip
	reverse_proxy app:8000
	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "DENY"
		Referrer-Policy "no-referrer"
	}
}
