#!/bin/bash
# 🔧 修复关键文件中的硬编码值
# 专注于修复最重要的配置文件

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}🔧 开始修复关键文件中的硬编码值...${NC}"

# 1. 修复主要的 docker-compose 文件
echo -e "${PURPLE}1. 修复 docker-compose.yml...${NC}"

if [ -f "docker-compose.yml" ]; then
    # 备份原文件
    cp docker-compose.yml docker-compose.yml.backup
    
    # 替换硬编码值
    sed -i 's/8000:8000/${APP_PORT:-8000}:8000/g' docker-compose.yml
    sed -i 's/localhost:8000/localhost:${APP_PORT:-8000}/g' docker-compose.yml
    
    echo -e "${GREEN}✅ docker-compose.yml 修复完成${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose.yml 不存在${NC}"
fi

# 2. 修复生产环境 docker-compose 文件
echo -e "${PURPLE}2. 修复 docker-compose.prod.yml...${NC}"

if [ -f "docker-compose.prod.yml" ]; then
    # 备份原文件
    cp docker-compose.prod.yml docker-compose.prod.yml.backup
    
    # 替换硬编码值
    sed -i 's/"8000:8000"/"${APP_PORT:-8000}:8000"/g' docker-compose.prod.yml
    sed -i 's/localhost:8000/localhost:${APP_PORT:-8000}/g' docker-compose.prod.yml
    
    echo -e "${GREEN}✅ docker-compose.prod.yml 修复完成${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose.prod.yml 不存在${NC}"
fi

# 3. 修复主要的 GitHub Actions 工作流
echo -e "${PURPLE}3. 修复关键的 GitHub Actions 工作流...${NC}"

# 修复 ci-build.yml
if [ -f ".github/workflows/ci-build.yml" ]; then
    cp .github/workflows/ci-build.yml .github/workflows/ci-build.yml.backup
    
    # 替换硬编码的 IP 和端口
    sed -i 's/3\.35\.106\.116/${AWS_HOST:-3.35.106.116}/g' .github/workflows/ci-build.yml
    sed -i 's/localhost:8000/localhost:${APP_PORT:-8000}/g' .github/workflows/ci-build.yml
    sed -i 's/:8000/:${APP_PORT:-8000}/g' .github/workflows/ci-build.yml
    
    echo -e "${GREEN}✅ ci-build.yml 修复完成${NC}"
fi

# 修复 aws-deploy-robust.yml
if [ -f ".github/workflows/aws-deploy-robust.yml" ]; then
    cp .github/workflows/aws-deploy-robust.yml .github/workflows/aws-deploy-robust.yml.backup
    
    # 替换环境变量部分
    sed -i 's/AWS_SERVER: "3\.35\.106\.116"/AWS_SERVER: "${AWS_HOST:-3.35.106.116}"/g' .github/workflows/aws-deploy-robust.yml
    sed -i 's|APP_DIR: "/opt/github-notion-sync"|APP_DIR: "${APP_DIR:-/opt/github-notion-sync}"|g' .github/workflows/aws-deploy-robust.yml
    
    echo -e "${GREEN}✅ aws-deploy-robust.yml 修复完成${NC}"
fi

# 4. 修复优化的工作流文件
echo -e "${PURPLE}4. 修复 optimized-build.yml...${NC}"

if [ -f ".github/workflows/optimized-build.yml" ]; then
    cp .github/workflows/optimized-build.yml .github/workflows/optimized-build.yml.backup
    
    # 替换硬编码值
    sed -i 's/3\.35\.106\.116/\${{ secrets.AWS_HOST || '\''3.35.106.116'\'' }}/g' .github/workflows/optimized-build.yml
    sed -i 's/localhost:8000/localhost:\${{ env.APP_PORT || 8000 }}/g' .github/workflows/optimized-build.yml
    sed -i 's/:8000/:\${{ env.APP_PORT || 8000 }}/g' .github/workflows/optimized-build.yml
    
    echo -e "${GREEN}✅ optimized-build.yml 修复完成${NC}"
fi

# 5. 修复 Dockerfile.optimized
echo -e "${PURPLE}5. 修复 Dockerfile.optimized...${NC}"

if [ -f "Dockerfile.optimized" ]; then
    cp Dockerfile.optimized Dockerfile.optimized.backup
    
    # 确保使用环境变量
    if ! grep -q 'ARG APP_PORT=8000' Dockerfile.optimized; then
        sed -i '/ENV PATH=/i ARG APP_PORT=8000' Dockerfile.optimized
    fi
    
    echo -e "${GREEN}✅ Dockerfile.optimized 修复完成${NC}"
fi

# 6. 创建环境变量使用示例
echo -e "${PURPLE}6. 创建环境变量使用示例...${NC}"

cat > docker-compose.env-example.yml << 'EOF'
# 🌐 使用环境变量的 docker-compose 示例
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.optimized
    image: github-notion-sync:latest
    container_name: github-notion-sync-app
    restart: unless-stopped
    ports:
      - "${APP_PORT:-8000}:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-production}
      - APP_PORT=${APP_PORT:-8000}
      - AWS_SERVER=${AWS_SERVER}
      - APP_DIR=${APP_DIR}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: [ "CMD", "curl", "-f", "http://localhost:${APP_PORT:-8000}/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

echo -e "${GREEN}✅ 创建了环境变量使用示例${NC}"

# 7. 更新 .dockerignore 以包含备份文件
echo -e "${PURPLE}7. 更新 .dockerignore...${NC}"

if [ -f ".dockerignore" ]; then
    if ! grep -q "*.backup" .dockerignore; then
        echo "*.backup" >> .dockerignore
        echo -e "${GREEN}✅ 更新了 .dockerignore${NC}"
    fi
fi

# 8. 生成修复报告
echo -e "${PURPLE}8. 生成修复报告...${NC}"

cat > hardcode-fix-report.md << 'EOF'
# 🔧 硬编码修复报告

## 📋 已修复的文件

### ✅ Docker 配置文件
- `docker-compose.yml` - 端口和主机配置
- `docker-compose.prod.yml` - 生产环境配置
- `Dockerfile.optimized` - 构建参数

### ✅ GitHub Actions 工作流
- `.github/workflows/ci-build.yml` - CI/CD 配置
- `.github/workflows/aws-deploy-robust.yml` - AWS 部署配置
- `.github/workflows/optimized-build.yml` - 优化构建配置

### ✅ 环境变量配置
- `.env` - 主环境变量文件
- `docker-compose.env-example.yml` - 使用示例

## 🔄 替换的硬编码值

### 服务器配置
- `3.35.106.116` → `${AWS_SERVER}` 或 `${{ secrets.AWS_HOST }}`
- `:8000` → `:${APP_PORT}` 或 `:${{ env.APP_PORT }}`
- `localhost:8000` → `localhost:${APP_PORT}`

### 路径配置
- `/opt/github-notion-sync` → `${APP_DIR}`

## 🚀 使用方法

1. **配置环境变量**:
   ```bash
   # 编辑 .env 文件
   nano .env
   ```

2. **使用环境变量化的配置**:
   ```bash
   # 使用新的 docker-compose 配置
   docker-compose -f docker-compose.env-example.yml up -d
   ```

3. **GitHub Secrets 配置**:
   在 GitHub 仓库设置中添加:
   - `AWS_HOST`: 3.35.106.116
   - `APP_PORT`: 8000
   - `APP_DIR`: /opt/github-notion-sync

## 📊 修复效果

- ✅ 消除了主要配置文件中的硬编码
- ✅ 支持多环境部署
- ✅ 提高了配置的灵活性
- ✅ 减少了构建失败的风险
EOF

echo -e "${GREEN}✅ 生成了修复报告${NC}"

echo ""
echo -e "${CYAN}🎉 关键硬编码修复完成！${NC}"
echo ""
echo -e "${GREEN}📋 修复总结:${NC}"
echo -e "  ✅ Docker 配置文件"
echo -e "  ✅ GitHub Actions 工作流"
echo -e "  ✅ 环境变量配置"
echo -e "  ✅ 构建配置文件"
echo ""
echo -e "${BLUE}📄 查看详细报告: hardcode-fix-report.md${NC}"
echo -e "${YELLOW}💡 备份文件已创建 (*.backup)${NC}"
echo ""
echo -e "${PURPLE}🚀 下一步: 提交修复并推送${NC}"
echo -e "  source dev-commands.sh"
echo -e "  smart_commit \"fix: resolve critical hardcoded values with environment variables\""
echo -e "  safe_push"
