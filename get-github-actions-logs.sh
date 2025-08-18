#!/bin/bash
# 🔍 获取 GitHub Actions 构建日志
# 分析具体的构建失败原因

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 获取 GitHub Actions 构建日志...${NC}"

# 创建日志目录
mkdir -p github-actions-logs

# 1. 检查当前 Git 状态
echo -e "${BLUE}1. 检查当前 Git 状态...${NC}"
git log --oneline -5 > github-actions-logs/recent-commits.log
echo "最近的提交:"
cat github-actions-logs/recent-commits.log

# 2. 分析工作流文件冲突
echo -e "${BLUE}2. 分析工作流文件...${NC}"

echo "=== 工作流文件列表 ===" > github-actions-logs/workflow-analysis.log
ls -la .github/workflows/ >> github-actions-logs/workflow-analysis.log

echo -e "\n=== 检查工作流触发条件 ===" >> github-actions-logs/workflow-analysis.log

# 检查哪些工作流会在 push 到 main 时触发
workflows_on_push=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        echo "检查 $workflow_name..." >> github-actions-logs/workflow-analysis.log
        
        if grep -q "push:" "$workflow" && grep -q "main\|master" "$workflow"; then
            workflows_on_push+=("$workflow_name")
            echo "  ✅ 会在 push 时触发" >> github-actions-logs/workflow-analysis.log
        else
            echo "  ❌ 不会在 push 时触发" >> github-actions-logs/workflow-analysis.log
        fi
    fi
done

echo -e "\n=== 会被触发的工作流 ===" >> github-actions-logs/workflow-analysis.log
printf '%s\n' "${workflows_on_push[@]}" >> github-actions-logs/workflow-analysis.log

echo "发现 ${#workflows_on_push[@]} 个会被触发的工作流:"
printf '%s\n' "${workflows_on_push[@]}"

# 3. 检查工作流文件语法
echo -e "${BLUE}3. 检查工作流文件语法...${NC}"

echo "=== YAML 语法检查 ===" > github-actions-logs/yaml-syntax-check.log

for workflow in "${workflows_on_push[@]}"; do
    workflow_path=".github/workflows/$workflow"
    echo "检查 $workflow 语法..." >> github-actions-logs/yaml-syntax-check.log
    
    if python3 -c "import yaml; yaml.safe_load(open('$workflow_path'))" 2>/dev/null; then
        echo "  ✅ $workflow 语法正确" >> github-actions-logs/yaml-syntax-check.log
    else
        echo "  ❌ $workflow 语法错误" >> github-actions-logs/yaml-syntax-check.log
        python3 -c "import yaml; yaml.safe_load(open('$workflow_path'))" >> github-actions-logs/yaml-syntax-check.log 2>&1 || true
    fi
done

# 4. 模拟 GitHub Actions 环境并获取详细日志
echo -e "${BLUE}4. 模拟 GitHub Actions 构建...${NC}"

# 设置 GitHub Actions 环境变量
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="CI Build"
export GITHUB_RUN_ID="debug-$(date +%s)"
export GITHUB_REPOSITORY="xupeng211/github-notion"
export GITHUB_REF="refs/heads/main"
export RUNNER_OS="Linux"
export RUNNER_ARCH="X64"

# 模拟主要工作流的构建步骤
for workflow in "${workflows_on_push[@]}"; do
    echo -e "${PURPLE}模拟 $workflow...${NC}"
    
    workflow_path=".github/workflows/$workflow"
    log_file="github-actions-logs/${workflow%.yml}-simulation.log"
    
    echo "=== $workflow 模拟构建 ===" > "$log_file"
    echo "时间: $(date)" >> "$log_file"
    echo "工作流文件: $workflow_path" >> "$log_file"
    echo "" >> "$log_file"
    
    # 检查工作流是否使用 Docker 构建
    if grep -q "docker build\|Dockerfile" "$workflow_path"; then
        echo "检测到 Docker 构建步骤" >> "$log_file"
        
        # 提取 Dockerfile 路径
        dockerfile_path=$(grep -o "Dockerfile[^[:space:]]*" "$workflow_path" | head -1 || echo "Dockerfile")
        if [ ! -f "$dockerfile_path" ]; then
            dockerfile_path="./Dockerfile.github"
        fi
        
        echo "使用 Dockerfile: $dockerfile_path" >> "$log_file"
        
        if [ -f "$dockerfile_path" ]; then
            echo "开始 Docker 构建..." >> "$log_file"
            
            # 执行 Docker 构建
            image_name="test-${workflow%.yml}:$(date +%s)"
            if docker build --progress=plain -f "$dockerfile_path" -t "$image_name" . >> "$log_file" 2>&1; then
                echo "✅ Docker 构建成功" >> "$log_file"
                
                # 测试容器启动
                echo "测试容器启动..." >> "$log_file"
                container_name="test-${workflow%.yml}-$(date +%s)"
                
                if docker run -d --name "$container_name" \
                    -e ENVIRONMENT=ci \
                    -e GITHUB_TOKEN=placeholder_token \
                    -e GITHUB_WEBHOOK_SECRET=placeholder_secret \
                    -e NOTION_TOKEN=placeholder_notion \
                    -e NOTION_DATABASE_ID=placeholder_db \
                    -e DEADLETTER_REPLAY_TOKEN=placeholder_replay \
                    "$image_name" >> "$log_file" 2>&1; then
                    
                    echo "✅ 容器启动成功" >> "$log_file"
                    
                    # 等待应用启动
                    sleep 10
                    
                    # 获取容器日志
                    echo "=== 容器日志 ===" >> "$log_file"
                    docker logs "$container_name" >> "$log_file" 2>&1
                    
                    # 清理容器
                    docker stop "$container_name" 2>/dev/null || true
                    docker rm "$container_name" 2>/dev/null || true
                else
                    echo "❌ 容器启动失败" >> "$log_file"
                fi
                
                # 清理镜像
                docker rmi "$image_name" 2>/dev/null || true
            else
                echo "❌ Docker 构建失败" >> "$log_file"
                
                # 分析构建失败原因
                echo "=== 构建失败分析 ===" >> "$log_file"
                if grep -q "pip install" "$log_file"; then
                    echo "检测到 pip 安装问题" >> "$log_file"
                fi
                if grep -q "COPY\|ADD" "$log_file"; then
                    echo "检测到文件复制问题" >> "$log_file"
                fi
                if grep -q "RUN.*failed" "$log_file"; then
                    echo "检测到命令执行问题" >> "$log_file"
                fi
            fi
        else
            echo "❌ Dockerfile 不存在: $dockerfile_path" >> "$log_file"
        fi
    else
        echo "未检测到 Docker 构建步骤" >> "$log_file"
    fi
    
    echo "完成 $workflow 模拟" >> "$log_file"
    echo ""
done

# 5. 检查工作流冲突
echo -e "${BLUE}5. 检查工作流冲突...${NC}"

echo "=== 工作流冲突分析 ===" > github-actions-logs/workflow-conflicts.log

# 检查是否有多个工作流使用相同的触发条件
echo "检查触发条件冲突..." >> github-actions-logs/workflow-conflicts.log

push_workflows=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ] && grep -q "push:" "$workflow"; then
        push_workflows+=("$(basename "$workflow")")
    fi
done

if [ ${#push_workflows[@]} -gt 1 ]; then
    echo "⚠️  发现多个工作流使用 push 触发:" >> github-actions-logs/workflow-conflicts.log
    printf '%s\n' "${push_workflows[@]}" >> github-actions-logs/workflow-conflicts.log
    echo "这可能导致并发构建和资源冲突" >> github-actions-logs/workflow-conflicts.log
else
    echo "✅ 没有发现触发条件冲突" >> github-actions-logs/workflow-conflicts.log
fi

# 检查备份文件
backup_files=($(ls .github/workflows/*.backup 2>/dev/null || true))
if [ ${#backup_files[@]} -gt 0 ]; then
    echo "⚠️  发现备份文件:" >> github-actions-logs/workflow-conflicts.log
    printf '%s\n' "${backup_files[@]}" >> github-actions-logs/workflow-conflicts.log
    echo "建议清理这些备份文件" >> github-actions-logs/workflow-conflicts.log
fi

# 6. 生成综合报告
echo -e "${BLUE}6. 生成综合报告...${NC}"

cat > github-actions-logs/comprehensive-report.md << 'EOF'
# 🔍 GitHub Actions 构建失败分析报告

## 📋 分析结果

### 🔧 工作流配置
- 工作流文件分析: workflow-analysis.log
- YAML 语法检查: yaml-syntax-check.log
- 工作流冲突检查: workflow-conflicts.log

### 🐳 构建模拟
- 各工作流模拟结果: *-simulation.log
- Docker 构建详细日志
- 容器启动测试结果

### 📊 问题识别

#### 常见问题类型
1. **工作流冲突**: 多个工作流同时触发
2. **YAML 语法错误**: 工作流文件格式问题
3. **Docker 构建失败**: Dockerfile 或依赖问题
4. **容器启动失败**: 环境变量或配置问题

#### 黄色文件名问题
黄色文件名通常表示:
- 文件有语法错误
- 文件有冲突
- 文件被修改但未提交
- 文件权限问题

## 💡 修复建议

### 如果是工作流冲突
1. 禁用不必要的工作流
2. 合并重复的工作流
3. 使用不同的触发条件

### 如果是 YAML 语法错误
1. 检查缩进和格式
2. 验证 YAML 语法
3. 修复语法错误

### 如果是 Docker 构建问题
1. 检查 Dockerfile 语法
2. 验证依赖版本
3. 检查文件路径

## 🚀 下一步行动

基于分析结果，提供具体的修复步骤。

EOF

echo -e "${GREEN}✅ GitHub Actions 日志分析完成！${NC}"
echo -e "${BLUE}📄 综合报告: github-actions-logs/comprehensive-report.md${NC}"
echo -e "${YELLOW}📁 所有日志文件保存在: github-actions-logs/${NC}"

# 显示关键发现
echo -e "\n${CYAN}🎯 关键发现总结:${NC}"

echo "工作流文件数量: $(ls .github/workflows/*.yml | wc -l)"
echo "会被触发的工作流: ${#workflows_on_push[@]}"

if [ ${#workflows_on_push[@]} -gt 1 ]; then
    echo -e "${YELLOW}⚠️  发现多个工作流会被触发，可能导致冲突${NC}"
fi

if [ ${#backup_files[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 ${#backup_files[@]} 个备份文件，建议清理${NC}"
fi

echo -e "\n${PURPLE}🔍 请查看详细日志文件以获取更多信息${NC}"
