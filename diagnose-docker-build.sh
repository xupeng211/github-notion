#!/bin/bash
# 🔍 Docker 构建问题诊断脚本
# 分析和修复 Docker 构建失败的问题

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Docker 构建问题诊断${NC}"
echo "=================================="

# 1. 检查代码质量问题
echo -e "${BLUE}📋 检查代码质量问题...${NC}"
if flake8 app/server.py --max-line-length=120 --ignore=E203,W503; then
    echo -e "${GREEN}✅ app/server.py 代码质量检查通过${NC}"
else
    echo -e "${RED}❌ app/server.py 存在代码质量问题${NC}"
    echo -e "${YELLOW}💡 正在自动修复...${NC}"
    black app/server.py
    isort app/server.py
fi

# 2. 检查 Python 语法
echo -e "${BLUE}📋 检查 Python 语法...${NC}"
if python -c "import ast; ast.parse(open('app/server.py').read())"; then
    echo -e "${GREEN}✅ app/server.py 语法正确${NC}"
else
    echo -e "${RED}❌ app/server.py 语法错误${NC}"
    exit 1
fi

# 3. 检查导入问题
echo -e "${BLUE}📋 检查导入问题...${NC}"
if python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.server import app
    print('✅ 导入成功')
except Exception as e:
    print(f'❌ 导入失败: {e}')
    exit(1)
"; then
    echo -e "${GREEN}✅ 导入检查通过${NC}"
else
    echo -e "${RED}❌ 导入检查失败${NC}"
fi

# 4. 检查 requirements.txt
echo -e "${BLUE}📋 检查 requirements.txt...${NC}"
if pip check > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 依赖包兼容性检查通过${NC}"
else
    echo -e "${YELLOW}⚠️ 依赖包可能存在冲突${NC}"
fi

# 5. 模拟 Docker 构建环境
echo -e "${BLUE}📋 模拟 Docker 构建环境...${NC}"

# 检查关键文件
files=("Dockerfile" "requirements.txt" "app/__init__.py" "app/server.py")
for file in "${files[@]}"; do
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅ $file 存在${NC}"
    else
        echo -e "${RED}❌ $file 缺失${NC}"
        if [[ "$file" == "app/__init__.py" ]]; then
            echo "创建 app/__init__.py..."
            touch app/__init__.py
        fi
    fi
done

# 6. 检查 Docker 构建上下文
echo -e "${BLUE}📋 检查 Docker 构建上下文...${NC}"
echo "构建上下文大小:"
du -sh . | head -1

echo "主要文件:"
find . -name "*.py" -o -name "Dockerfile" -o -name "requirements.txt" | head -10

# 7. 生成修复建议
echo -e "${BLUE}💡 修复建议:${NC}"
echo "1. 确保所有 Python 文件语法正确"
echo "2. 检查 requirements.txt 中的包版本"
echo "3. 确保 app/__init__.py 文件存在"
echo "4. 检查 Docker 构建日志中的具体错误"

# 8. 创建简化的 Dockerfile 用于测试
echo -e "${BLUE}📋 创建测试用 Dockerfile...${NC}"
cat > Dockerfile.test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装基础依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

echo -e "${GREEN}✅ 创建了简化的 Dockerfile.test${NC}"
echo -e "${YELLOW}💡 可以使用以下命令测试构建:${NC}"
echo "docker build -f Dockerfile.test -t github-notion-test ."

echo -e "${GREEN}🎉 诊断完成！${NC}"
