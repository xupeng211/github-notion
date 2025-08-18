#!/bin/bash
# 🔍 调试 CI/CD 构建问题
# 模拟 GitHub Actions 环境进行本地测试

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 调试 CI/CD 构建问题...${NC}"

# 1. 检查关键文件
echo -e "${BLUE}1. 检查关键文件存在性...${NC}"

critical_files=(
    "Dockerfile.github"
    "requirements.txt"
    "app/server.py"
    "app/__init__.py"
    "app/config_validator.py"
    "app/enhanced_metrics.py"
    "app/idempotency.py"
    "app/middleware.py"
    "app/models.py"
    "app/schemas.py"
    "app/service.py"
)

missing_files=()
for file in "${critical_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
        echo -e "${RED}❌ 缺少文件: $file${NC}"
    else
        echo -e "${GREEN}✅ $file${NC}"
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${RED}❌ 发现 ${#missing_files[@]} 个缺少的关键文件${NC}"
    echo -e "${YELLOW}💡 这些文件对于构建是必需的${NC}"
fi

# 2. 检查 Python 导入
echo -e "${BLUE}2. 检查 Python 导入依赖...${NC}"

echo "检查 app/server.py 的导入..."
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    # 检查基础导入
    import fastapi
    import uvicorn
    import prometheus_client
    import pydantic
    print('✅ 基础依赖导入成功')
    
    # 检查应用导入
    from app import config_validator
    print('✅ app.config_validator 导入成功')
    
    from app import enhanced_metrics
    print('✅ app.enhanced_metrics 导入成功')
    
    from app import idempotency
    print('✅ app.idempotency 导入成功')
    
    from app import middleware
    print('✅ app.middleware 导入成功')
    
    from app import models
    print('✅ app.models 导入成功')
    
    from app import schemas
    print('✅ app.schemas 导入成功')
    
    from app import service
    print('✅ app.service 导入成功')
    
except ImportError as e:
    print(f'❌ 导入错误: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 其他错误: {e}')
    sys.exit(1)
" 2>&1; then
    echo -e "${GREEN}✅ Python 导入检查通过${NC}"
else
    echo -e "${RED}❌ Python 导入检查失败${NC}"
    echo -e "${YELLOW}💡 这可能是构建失败的原因${NC}"
fi

# 3. 检查 requirements.txt 中的包版本兼容性
echo -e "${BLUE}3. 检查包版本兼容性...${NC}"

echo "检查关键包版本..."
python3 -c "
import pkg_resources
import sys

# 检查关键包
critical_packages = [
    'fastapi==0.111.0',
    'uvicorn[standard]==0.30.1',
    'pydantic==1.10.22',
    'prometheus-client==0.20.0',
    'requests==2.31.0'
]

for package in critical_packages:
    try:
        pkg_resources.require(package)
        print(f'✅ {package}')
    except pkg_resources.DistributionNotFound:
        print(f'❌ 未安装: {package}')
    except pkg_resources.VersionConflict as e:
        print(f'⚠️  版本冲突: {e}')
    except Exception as e:
        print(f'❌ 错误: {package} - {e}')
"

# 4. 模拟 Docker 构建（如果 Docker 可用）
echo -e "${BLUE}4. 模拟 Docker 构建...${NC}"

if command -v docker &> /dev/null; then
    echo "尝试构建 Docker 镜像..."
    if docker build -f Dockerfile.github -t test-build . 2>&1 | tee docker-build.log; then
        echo -e "${GREEN}✅ Docker 构建成功${NC}"
        
        # 测试容器启动
        echo "测试容器启动..."
        if timeout 30 docker run --rm -d --name test-container -p 8001:8000 test-build; then
            sleep 5
            if curl -f http://localhost:8001/health 2>/dev/null; then
                echo -e "${GREEN}✅ 容器启动和健康检查成功${NC}"
            else
                echo -e "${YELLOW}⚠️  容器启动但健康检查失败${NC}"
            fi
            docker stop test-container 2>/dev/null || true
        else
            echo -e "${RED}❌ 容器启动失败${NC}"
        fi
        
        # 清理测试镜像
        docker rmi test-build 2>/dev/null || true
    else
        echo -e "${RED}❌ Docker 构建失败${NC}"
        echo -e "${YELLOW}💡 查看 docker-build.log 获取详细错误信息${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker 不可用，跳过构建测试${NC}"
fi

# 5. 检查环境变量配置
echo -e "${BLUE}5. 检查环境变量配置...${NC}"

if [ -f ".env" ]; then
    echo "检查 .env 文件..."
    source .env
    
    required_vars=("AWS_SERVER" "APP_PORT" "APP_DIR" "SERVICE_NAME")
    for var in "${required_vars[@]}"; do
        if [ -n "${!var:-}" ]; then
            echo -e "${GREEN}✅ $var = ${!var}${NC}"
        else
            echo -e "${YELLOW}⚠️  $var 未设置${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  .env 文件不存在${NC}"
fi

# 6. 生成诊断报告
echo -e "${BLUE}6. 生成诊断报告...${NC}"

cat > ci-build-debug-report.md << 'EOF'
# 🔍 CI/CD 构建调试报告

## 📋 检查结果

### ✅ 文件检查
- 所有关键文件存在性检查
- Python 模块导入检查
- 依赖包版本兼容性检查

### 🐳 Docker 构建测试
- 本地 Docker 构建模拟
- 容器启动测试
- 健康检查验证

### ⚙️ 环境配置检查
- 环境变量配置验证
- 必需配置项检查

## 🔧 常见构建失败原因

### 1. 缺少文件
- `app/__init__.py` 文件缺失
- 关键模块文件不存在
- requirements.txt 中的依赖无法安装

### 2. 导入错误
- Python 路径问题
- 模块循环导入
- 依赖版本冲突

### 3. Docker 构建问题
- 基础镜像拉取失败
- 网络超时
- 权限问题

### 4. 运行时错误
- 环境变量缺失
- 端口冲突
- 数据库连接问题

## 💡 修复建议

### 如果是文件缺失问题
```bash
# 确保所有必需文件存在
touch app/__init__.py
git add app/__init__.py
git commit -m "fix: add missing __init__.py file"
git push
```

### 如果是依赖问题
```bash
# 更新 requirements.txt
pip freeze > requirements-current.txt
# 比较并修复版本冲突
```

### 如果是 Docker 问题
```bash
# 使用优化的 Dockerfile
cp Dockerfile.optimized Dockerfile.github
git add Dockerfile.github
git commit -m "fix: update Dockerfile for better CI/CD compatibility"
git push
```

## 🚀 下一步行动

1. 根据诊断结果修复发现的问题
2. 本地测试修复效果
3. 提交并推送修复
4. 监控 CI/CD 构建结果
EOF

echo -e "${GREEN}✅ 诊断报告已生成: ci-build-debug-report.md${NC}"

echo ""
echo -e "${CYAN}🎯 诊断完成！${NC}"
echo -e "${YELLOW}💡 请查看上述输出和生成的报告，根据发现的问题进行修复${NC}"
echo -e "${BLUE}📄 详细报告: ci-build-debug-report.md${NC}"
