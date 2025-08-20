#!/bin/bash
# 🧪 运行时冒烟验证脚本
# 基于构建产物镜像进行最小冒烟测试

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 运行时冒烟验证开始${NC}"
echo "=================================================="

# 读取镜像tag（与当前提交SHA一致）
CI_COMMIT_SHA=${CI_COMMIT_SHA:-$(git rev-parse --short HEAD)}
REGISTRY_SERVER=${REGISTRY_SERVER:-"ghcr.io"}
CI_PROJECT_PATH=${CI_PROJECT_PATH:-"xupeng211/github-notion"}
IMG="${REGISTRY_SERVER}/${CI_PROJECT_PATH}/app:${CI_COMMIT_SHA}"

echo -e "${BLUE}📋 测试配置:${NC}"
echo "  镜像: $IMG"
echo "  提交SHA: $CI_COMMIT_SHA"
echo ""

# 清理可能存在的容器
docker rm -f app-smoke 2>/dev/null || true

echo -e "${BLUE}🐳 1) 启动容器...${NC}"
if docker run -d --rm --name app-smoke -p 8000:8000 "$IMG"; then
    echo -e "${GREEN}✅ 容器启动成功${NC}"
else
    echo -e "${RED}❌ 容器启动失败${NC}"
    exit 1
fi

# 等待容器启动
echo "等待容器启动..."
sleep 10

echo -e "\n${BLUE}🔍 2) 健康探针检查...${NC}"
HEALTH_STATUS="FAIL"
HTTP_CODE=""

if HTTP_CODE=$(curl -fsS -w "%{http_code}" -o /dev/null http://127.0.0.1:8000/health 2>/dev/null); then
    if [[ "$HTTP_CODE" == "200" ]]; then
        HEALTH_STATUS="OK"
        echo -e "${GREEN}✅ /health: OK (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${RED}❌ /health: FAIL (HTTP $HTTP_CODE)${NC}"
    fi
else
    echo -e "${RED}❌ /health: FAIL (连接失败)${NC}"
fi

echo -e "\n${BLUE}🔍 3) 指标端点检查...${NC}"
METRICS_STATUS="FAIL"
METRICS_CONTENT=""

if METRICS_CONTENT=$(curl -fsS -L http://127.0.0.1:8000/metrics 2>/dev/null); then
    if echo "$METRICS_CONTENT" | grep -q "python_info\|# HELP\|# TYPE"; then
        METRICS_STATUS="OK"
        echo -e "${GREEN}✅ /metrics: OK (包含Prometheus格式指标)${NC}"
        echo "指标样例:"
        echo "$METRICS_CONTENT" | head -n 5
    else
        METRICS_STATUS="PARTIAL"
        echo -e "${YELLOW}⚠️ /metrics: 可访问但格式异常${NC}"
        echo "响应内容: $(echo "$METRICS_CONTENT" | head -n 2)"
    fi
else
    echo -e "${YELLOW}⚠️ /metrics: SKIP (端点不可访问)${NC}"
    METRICS_STATUS="SKIP"
fi

echo -e "\n${BLUE}🔍 4) 关键依赖导入验证...${NC}"
DEPS_STATUS="FAIL"

if docker exec app-smoke python - <<'PY'
import importlib, sys
modules = ["fastapi", "sqlalchemy", "requests", "uvicorn", "pydantic"]
failed = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f"✅ {m}")
    except Exception as e:
        print(f"❌ {m}: {e}", file=sys.stderr)
        failed.append(m)

if failed:
    print(f"Failed modules: {failed}", file=sys.stderr)
    sys.exit(1)
else:
    print("All dependencies imported successfully")
PY
then
    DEPS_STATUS="OK"
    echo -e "${GREEN}✅ 依赖导入: OK${NC}"
else
    echo -e "${RED}❌ 依赖导入: FAIL${NC}"
fi

echo -e "\n${BLUE}🔍 5) 容器日志检查...${NC}"
echo "容器日志最后50行:"
echo "----------------------------------------"
docker logs --tail=50 app-smoke || true
echo "----------------------------------------"

echo -e "\n${BLUE}🧹 6) 清理容器...${NC}"
docker rm -f app-smoke || true

echo -e "\n${BLUE}📊 冒烟验证结果汇总:${NC}"
echo "=================================================="
echo -e "/health: ${HEALTH_STATUS} (HTTP ${HTTP_CODE:-N/A})"
echo -e "/metrics: ${METRICS_STATUS}"
echo -e "依赖导入: ${DEPS_STATUS} (fastapi, sqlalchemy, requests, uvicorn, pydantic)"
echo -e "容器启动: OK"

if [[ "$HEALTH_STATUS" == "OK" && "$DEPS_STATUS" == "OK" ]]; then
    echo -e "\n${GREEN}🎉 冒烟验证通过！镜像可用于生产部署${NC}"
    exit 0
else
    echo -e "\n${RED}❌ 冒烟验证失败！请检查上述问题${NC}"
    
    # 生成结构化诊断
    cat <<EOF

STRUCTURED_JSON 诊断:
{
  "root_causes": [
    "$([ "$HEALTH_STATUS" != "OK" ] && echo "健康检查端点失败")",
    "$([ "$DEPS_STATUS" != "OK" ] && echo "关键依赖导入失败")"
  ],
  "evidence": {
    "health_endpoint": "$HEALTH_STATUS",
    "http_code": "$HTTP_CODE",
    "dependencies": "$DEPS_STATUS",
    "container_logs": "见上方日志输出"
  },
  "suggested_fixes": [
    "检查应用启动脚本和端口配置",
    "验证requirements.txt中的依赖版本",
    "检查Dockerfile中的COPY指令是否正确",
    "确认健康检查端点路径和实现"
  ]
}
EOF
    exit 1
fi
