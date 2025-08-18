#!/bin/bash
# 🔍 分析当前 CI/CD 构建失败
# 获取最新的构建日志和详细错误信息

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 分析当前 CI/CD 构建失败...${NC}"

# 创建分析目录
mkdir -p current-build-analysis

# 1. 检查当前工作流状态
echo -e "${BLUE}1. 检查当前工作流状态...${NC}"

echo "=== 当前工作流文件 ===" > current-build-analysis/current-workflows.log
ls -la .github/workflows/ >> current-build-analysis/current-workflows.log

echo "当前工作流文件:"
ls .github/workflows/*.yml 2>/dev/null || echo "没有找到 .yml 工作流文件"

# 检查是否有新的工作流文件
active_workflows=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        active_workflows+=("$workflow_name")
        echo "发现工作流: $workflow_name"
    fi
done

echo "活跃工作流数量: ${#active_workflows[@]}"

# 2. 检查最新的 Git 提交
echo -e "${BLUE}2. 检查最新提交...${NC}"

git log --oneline -5 > current-build-analysis/recent-commits.log
echo "最近的提交:"
cat current-build-analysis/recent-commits.log

# 3. 模拟当前的构建环境
echo -e "${BLUE}3. 模拟当前构建环境...${NC}"

# 设置环境变量
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="Current Build Analysis"
export GITHUB_RUN_ID="analysis-$(date +%s)"

# 检查每个活跃的工作流
for workflow in "${active_workflows[@]}"; do
    echo -e "${PURPLE}分析 $workflow...${NC}"
    
    workflow_path=".github/workflows/$workflow"
    analysis_log="current-build-analysis/${workflow%.yml}-analysis.log"
    
    echo "=== $workflow 分析 ===" > "$analysis_log"
    echo "时间: $(date)" >> "$analysis_log"
    echo "工作流文件: $workflow_path" >> "$analysis_log"
    echo "" >> "$analysis_log"
    
    # 检查工作流语法
    echo "检查 YAML 语法..." >> "$analysis_log"
    if python3 -c "import yaml; yaml.safe_load(open('$workflow_path'))" 2>/dev/null; then
        echo "✅ YAML 语法正确" >> "$analysis_log"
    else
        echo "❌ YAML 语法错误:" >> "$analysis_log"
        python3 -c "import yaml; yaml.safe_load(open('$workflow_path'))" >> "$analysis_log" 2>&1 || true
        continue
    fi
    
    # 检查触发条件
    echo "检查触发条件..." >> "$analysis_log"
    if grep -q "push:" "$workflow_path"; then
        echo "✅ 配置了 push 触发" >> "$analysis_log"
        
        # 检查分支配置
        if grep -A 5 "push:" "$workflow_path" | grep -q "main\|master"; then
            echo "✅ 会在 main 分支触发" >> "$analysis_log"
        else
            echo "⚠️  push 触发但未指定 main 分支" >> "$analysis_log"
        fi
    else
        echo "ℹ️  未配置 push 触发" >> "$analysis_log"
    fi
    
    # 检查 Docker 构建步骤
    if grep -q "docker build\|Dockerfile" "$workflow_path"; then
        echo "检测到 Docker 构建步骤" >> "$analysis_log"
        
        # 提取 Dockerfile 路径
        dockerfile_path=$(grep -o "Dockerfile[^[:space:]]*" "$workflow_path" | head -1 || echo "Dockerfile")
        if [ ! -f "$dockerfile_path" ]; then
            dockerfile_path="./Dockerfile.github"
        fi
        
        echo "使用 Dockerfile: $dockerfile_path" >> "$analysis_log"
        
        if [ -f "$dockerfile_path" ]; then
            echo "开始实际 Docker 构建测试..." >> "$analysis_log"
            
            # 执行实际的 Docker 构建
            image_name="current-test-${workflow%.yml}:$(date +%s)"
            
            echo "构建命令: docker build -f $dockerfile_path -t $image_name ." >> "$analysis_log"
            echo "开始构建..." >> "$analysis_log"
            
            if timeout 300 docker build --progress=plain -f "$dockerfile_path" -t "$image_name" . >> "$analysis_log" 2>&1; then
                echo "✅ Docker 构建成功" >> "$analysis_log"
                
                # 测试容器启动
                echo "测试容器启动..." >> "$analysis_log"
                container_name="current-test-${workflow%.yml}-$(date +%s)"
                
                if docker run -d --name "$container_name" \
                    -p 8091:8000 \
                    -e ENVIRONMENT=ci \
                    -e GITHUB_TOKEN=placeholder_token \
                    -e GITHUB_WEBHOOK_SECRET=placeholder_secret \
                    -e NOTION_TOKEN=placeholder_notion \
                    -e NOTION_DATABASE_ID=placeholder_db \
                    -e DEADLETTER_REPLAY_TOKEN=placeholder_replay \
                    "$image_name" >> "$analysis_log" 2>&1; then
                    
                    echo "✅ 容器启动成功" >> "$analysis_log"
                    
                    # 等待应用启动
                    sleep 15
                    
                    # 检查容器状态
                    if docker ps | grep -q "$container_name"; then
                        echo "✅ 容器正在运行" >> "$analysis_log"
                        
                        # 获取容器日志
                        echo "=== 容器启动日志 ===" >> "$analysis_log"
                        docker logs "$container_name" >> "$analysis_log" 2>&1
                        
                        # 测试健康检查
                        echo "=== 健康检查测试 ===" >> "$analysis_log"
                        
                        # 测试 CI 健康检查
                        if curl -f -m 10 http://localhost:8091/health/ci > /tmp/health-ci-current.json 2>&1; then
                            echo "✅ CI 健康检查成功" >> "$analysis_log"
                            cat /tmp/health-ci-current.json >> "$analysis_log"
                        else
                            echo "❌ CI 健康检查失败" >> "$analysis_log"
                            curl -v -m 10 http://localhost:8091/health/ci >> "$analysis_log" 2>&1 || true
                        fi
                        
                        # 测试标准健康检查
                        if curl -f -m 10 http://localhost:8091/health > /tmp/health-standard-current.json 2>&1; then
                            echo "✅ 标准健康检查成功" >> "$analysis_log"
                        else
                            echo "❌ 标准健康检查失败" >> "$analysis_log"
                        fi
                        
                    else
                        echo "❌ 容器已停止" >> "$analysis_log"
                        docker logs "$container_name" >> "$analysis_log" 2>&1 || true
                    fi
                    
                    # 清理容器
                    docker stop "$container_name" 2>/dev/null || true
                    docker rm "$container_name" 2>/dev/null || true
                else
                    echo "❌ 容器启动失败" >> "$analysis_log"
                fi
                
                # 清理镜像
                docker rmi "$image_name" 2>/dev/null || true
                
            else
                echo "❌ Docker 构建失败" >> "$analysis_log"
                
                # 分析构建失败的具体原因
                echo "=== 构建失败分析 ===" >> "$analysis_log"
                
                # 检查常见错误模式
                if grep -q "pip.*failed\|pip.*error" "$analysis_log"; then
                    echo "🔍 检测到 pip 安装错误" >> "$analysis_log"
                    grep -A 5 -B 5 "pip.*failed\|pip.*error" "$analysis_log" | tail -20 >> "$analysis_log"
                fi
                
                if grep -q "COPY.*failed\|ADD.*failed\|No such file" "$analysis_log"; then
                    echo "🔍 检测到文件复制错误" >> "$analysis_log"
                    grep -A 3 -B 3 "COPY.*failed\|ADD.*failed\|No such file" "$analysis_log" >> "$analysis_log"
                fi
                
                if grep -q "RUN.*failed\|command not found" "$analysis_log"; then
                    echo "🔍 检测到命令执行错误" >> "$analysis_log"
                    grep -A 5 -B 5 "RUN.*failed\|command not found" "$analysis_log" >> "$analysis_log"
                fi
                
                if grep -q "requirements.txt" "$analysis_log"; then
                    echo "🔍 检测到依赖安装问题" >> "$analysis_log"
                    grep -A 10 -B 5 "requirements.txt" "$analysis_log" | tail -20 >> "$analysis_log"
                fi
                
                # 获取最后的错误信息
                echo "=== 最后的错误信息 ===" >> "$analysis_log"
                tail -30 "$analysis_log" | grep -E "ERROR|error|Error|failed|Failed|FAILED" >> "$analysis_log" || echo "未找到明确的错误信息" >> "$analysis_log"
            fi
        else
            echo "❌ Dockerfile 不存在: $dockerfile_path" >> "$analysis_log"
        fi
    else
        echo "ℹ️  未检测到 Docker 构建步骤" >> "$analysis_log"
    fi
    
    echo "完成 $workflow 分析" >> "$analysis_log"
done

# 4. 检查系统资源和环境
echo -e "${BLUE}4. 检查系统环境...${NC}"

echo "=== 系统环境检查 ===" > current-build-analysis/system-check.log
echo "Docker 版本:" >> current-build-analysis/system-check.log
docker --version >> current-build-analysis/system-check.log 2>&1

echo "Docker 状态:" >> current-build-analysis/system-check.log
docker info >> current-build-analysis/system-check.log 2>&1

echo "磁盘空间:" >> current-build-analysis/system-check.log
df -h >> current-build-analysis/system-check.log 2>&1

echo "内存使用:" >> current-build-analysis/system-check.log
free -h >> current-build-analysis/system-check.log 2>&1

# 5. 生成综合分析报告
echo -e "${BLUE}5. 生成综合分析报告...${NC}"

cat > current-build-analysis/failure-analysis-report.md << 'EOF'
# 🔍 当前 CI/CD 构建失败分析报告

## 📋 分析概览

### 🔧 工作流状态
- 当前工作流文件: 检查 current-workflows.log
- 活跃工作流数量: 待分析
- YAML 语法检查: 各工作流分析日志

### 🐳 构建测试结果
- Docker 构建状态: 检查各 *-analysis.log
- 容器启动测试: 检查容器日志部分
- 健康检查结果: 检查健康检查测试部分

### 🖥️ 系统环境
- Docker 环境: system-check.log
- 资源使用情况: system-check.log

## 🎯 问题识别

### 常见失败模式

#### 1. Docker 构建失败
- **依赖安装错误**: pip 安装失败
- **文件复制错误**: COPY/ADD 指令失败
- **命令执行错误**: RUN 指令失败
- **基础镜像问题**: 镜像拉取失败

#### 2. 容器启动失败
- **环境变量问题**: 必需变量缺失
- **端口冲突**: 端口已被占用
- **配置错误**: 应用配置问题

#### 3. 健康检查失败
- **端点不存在**: /health/ci 端点缺失
- **应用未启动**: 应用启动失败
- **网络问题**: 连接超时

## 💡 修复建议

### 基于分析结果的具体建议

1. **如果是 Docker 构建失败**
   - 检查 requirements.txt 依赖版本
   - 验证 Dockerfile 语法
   - 确认所有必需文件存在

2. **如果是容器启动失败**
   - 检查环境变量配置
   - 验证端口配置
   - 检查应用启动日志

3. **如果是健康检查失败**
   - 确认 /health/ci 端点存在
   - 检查应用启动状态
   - 验证网络连接

## 🚀 下一步行动

基于具体的错误信息，提供针对性的修复步骤。

EOF

# 清理临时文件
rm -f /tmp/health-*-current.json

echo -e "${GREEN}✅ 当前构建失败分析完成！${NC}"
echo -e "${BLUE}📄 分析报告: current-build-analysis/failure-analysis-report.md${NC}"
echo -e "${YELLOW}📁 详细日志保存在: current-build-analysis/${NC}"

# 显示关键发现
echo -e "\n${CYAN}🎯 关键发现总结:${NC}"

echo "活跃工作流数量: ${#active_workflows[@]}"
if [ ${#active_workflows[@]} -eq 0 ]; then
    echo -e "${RED}❌ 没有发现活跃的工作流文件${NC}"
elif [ ${#active_workflows[@]} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  发现多个活跃工作流，可能存在冲突${NC}"
else
    echo -e "${GREEN}✅ 发现 1 个活跃工作流${NC}"
fi

# 检查是否有分析日志
for workflow in "${active_workflows[@]}"; do
    analysis_log="current-build-analysis/${workflow%.yml}-analysis.log"
    if [ -f "$analysis_log" ]; then
        if grep -q "✅ Docker 构建成功" "$analysis_log"; then
            echo -e "${GREEN}✅ $workflow: Docker 构建成功${NC}"
        elif grep -q "❌ Docker 构建失败" "$analysis_log"; then
            echo -e "${RED}❌ $workflow: Docker 构建失败${NC}"
            echo "主要错误:"
            grep -E "ERROR|error|Error|failed|Failed" "$analysis_log" | head -3 || echo "检查详细日志获取错误信息"
        fi
    fi
done

echo -e "\n${PURPLE}🔍 请查看详细分析日志以获取完整信息${NC}"
