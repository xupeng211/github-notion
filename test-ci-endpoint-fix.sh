#!/bin/bash
# 🧪 测试 CI 端点修复
# 强制重新构建并验证 /health/ci 端点

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🧪 测试 CI 端点修复...${NC}"

# 1. 清理所有相关容器和镜像
echo -e "${BLUE}1. 清理现有容器和镜像...${NC}"
docker-compose down 2>/dev/null || true
docker rmi github-notion-sync:latest 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# 2. 强制重新构建镜像
echo -e "${BLUE}2. 强制重新构建镜像...${NC}"
if docker-compose build --no-cache app; then
    echo "✅ 镜像重新构建成功"
else
    echo "❌ 镜像构建失败"
    exit 1
fi

# 3. 启动服务
echo -e "${BLUE}3. 启动服务...${NC}"
export ENVIRONMENT=ci
export APP_PORT=8000
export LOG_LEVEL=DEBUG

if docker-compose up -d app; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败"
    exit 1
fi

# 4. 等待服务完全启动
echo -e "${BLUE}4. 等待服务启动...${NC}"
echo "等待 45 秒确保应用完全启动..."
sleep 45

# 5. 检查容器状态
echo -e "${BLUE}5. 检查容器状态...${NC}"
if docker ps | grep -q github-notion-sync-app; then
    echo "✅ 容器正在运行"
    
    # 获取容器日志
    echo "最新容器日志:"
    docker logs --tail 15 github-notion-sync-app
    
else
    echo "❌ 容器未运行"
    docker ps -a | grep github-notion-sync || echo "未找到容器"
    exit 1
fi

# 6. 测试 CI 健康检查端点
echo -e "${BLUE}6. 测试 CI 健康检查端点...${NC}"

echo "测试 /health/ci 端点:"
if curl -f -v -m 15 http://localhost:8000/health/ci > /tmp/ci-health-test.json 2>&1; then
    echo "✅ CI 健康检查端点响应成功"
    echo "响应内容:"
    cat /tmp/ci-health-test.json
    
    # 检查状态
    if grep -q '"status":"healthy"' /tmp/ci-health-test.json; then
        echo "✅ 状态正确: healthy"
        ci_endpoint_works=true
    else
        echo "❌ 状态不正确"
        ci_endpoint_works=false
    fi
else
    echo "❌ CI 健康检查端点失败"
    echo "错误详情:"
    cat /tmp/ci-health-test.json 2>/dev/null || echo "无响应内容"
    ci_endpoint_works=false
fi

echo ""

# 7. 测试标准健康检查端点
echo -e "${BLUE}7. 测试标准健康检查端点...${NC}"

echo "测试 /health 端点:"
if curl -f -m 15 http://localhost:8000/health > /tmp/standard-health-test.json 2>&1; then
    echo "✅ 标准健康检查端点响应成功"
    
    # 检查状态
    status=$(grep -o '"status":"[^"]*"' /tmp/standard-health-test.json | cut -d'"' -f4)
    echo "状态: $status"
    standard_endpoint_works=true
else
    echo "❌ 标准健康检查端点失败"
    standard_endpoint_works=false
fi

# 8. 测试 Docker 健康检查
echo -e "${BLUE}8. 测试 Docker 健康检查...${NC}"

# 等待 Docker 健康检查完成
echo "等待 Docker 健康检查..."
sleep 30

health_status=$(docker inspect --format='{{.State.Health.Status}}' github-notion-sync-app 2>/dev/null || echo "unknown")
echo "Docker 健康检查状态: $health_status"

if [ "$health_status" = "healthy" ]; then
    echo "✅ Docker 健康检查通过"
    docker_health_works=true
else
    echo "❌ Docker 健康检查失败: $health_status"
    docker_health_works=false
fi

# 9. 模拟完整的 GitHub Actions 流程
echo -e "${BLUE}9. 模拟 GitHub Actions 流程...${NC}"

echo "模拟 GitHub Actions 健康检查流程..."

# 检查容器是否在运行
if docker ps | grep -q github-notion-sync-app; then
    echo "✅ 容器正在运行"
    
    # 检查 Docker 健康检查状态
    health_status=$(docker inspect --format='{{.State.Health.Status}}' github-notion-sync-app 2>/dev/null || echo "unknown")
    echo "Docker 健康检查状态: $health_status"
    
    if [ "$health_status" = "healthy" ] || [ "$health_status" = "unknown" ]; then
        echo "🧪 CI/CD 健康检查..."
        if curl -f http://localhost:8000/health/ci > /dev/null 2>&1; then
            echo "✅ 部署成功"
            github_actions_success=true
        else
            echo "❌ CI/CD 健康检查失败，尝试标准健康检查..."
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                echo "⚠️ 标准健康检查通过，但状态可能为 degraded"
                echo "✅ 部署成功（CI/CD 模式）"
                github_actions_success=true
            else
                echo "❌ 所有健康检查都失败"
                github_actions_success=false
            fi
        fi
    else
        echo "❌ Docker 健康检查失败: $health_status"
        github_actions_success=false
    fi
else
    echo "❌ 容器未运行"
    github_actions_success=false
fi

# 10. 清理
echo -e "${BLUE}10. 清理测试环境...${NC}"
docker-compose down
rm -f /tmp/*-health-test.json

# 11. 总结
echo -e "${BLUE}11. 测试总结...${NC}"

echo -e "\n${CYAN}📊 测试结果总结:${NC}"
echo -e "CI 健康检查端点: ${ci_endpoint_works:-false}"
echo -e "标准健康检查端点: ${standard_endpoint_works:-false}"
echo -e "Docker 健康检查: ${docker_health_works:-false}"
echo -e "GitHub Actions 模拟: ${github_actions_success:-false}"

if [ "${ci_endpoint_works:-false}" = "true" ] && [ "${github_actions_success:-false}" = "true" ]; then
    echo -e "\n${GREEN}🎉 测试成功！CI 端点修复有效${NC}"
    echo -e "${GREEN}✅ /health/ci 端点正常工作${NC}"
    echo -e "${GREEN}✅ GitHub Actions 流程应该能够成功${NC}"
    echo -e "${GREEN}✅ 可以安全推送到远程仓库${NC}"
    exit 0
else
    echo -e "\n${RED}❌ 测试失败！需要进一步调试${NC}"
    
    if [ "${ci_endpoint_works:-false}" = "false" ]; then
        echo -e "${YELLOW}💡 CI 健康检查端点不工作，检查代码是否正确部署${NC}"
    fi
    
    if [ "${docker_health_works:-false}" = "false" ]; then
        echo -e "${YELLOW}💡 Docker 健康检查失败，检查健康检查配置${NC}"
    fi
    
    echo -e "${YELLOW}💡 建议检查容器日志和应用代码${NC}"
    exit 1
fi
