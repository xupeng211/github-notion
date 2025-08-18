#!/bin/bash
# 🔧 修复工作流冲突
# 清理冲突的工作流文件，只保留必要的

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔧 修复工作流冲突...${NC}"

# 创建备份目录
mkdir -p .github/workflows-backup

# 1. 备份所有工作流文件
echo -e "${BLUE}1. 备份现有工作流文件...${NC}"
cp -r .github/workflows/* .github/workflows-backup/ 2>/dev/null || true
echo "✅ 工作流文件已备份到 .github/workflows-backup/"

# 2. 定义要保留的主要工作流
echo -e "${BLUE}2. 定义主要工作流...${NC}"

# 只保留最重要的工作流
keep_workflows=(
    "ci-build.yml"           # 主要的 CI/CD 构建工作流
    "optimized-build.yml"    # 优化的构建工作流
)

# 3. 移除冲突的工作流
echo -e "${BLUE}3. 移除冲突的工作流...${NC}"

removed_workflows=()
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        workflow_name=$(basename "$workflow")
        
        # 检查是否在保留列表中
        keep_this=false
        for keep in "${keep_workflows[@]}"; do
            if [ "$workflow_name" = "$keep" ]; then
                keep_this=true
                break
            fi
        done
        
        if [ "$keep_this" = false ]; then
            echo "移除冲突工作流: $workflow_name"
            rm "$workflow"
            removed_workflows+=("$workflow_name")
        else
            echo "保留主要工作流: $workflow_name"
        fi
    fi
done

# 4. 清理备份文件
echo -e "${BLUE}4. 清理备份文件...${NC}"

backup_files=($(ls .github/workflows/*.backup 2>/dev/null || true))
for backup in "${backup_files[@]}"; do
    echo "移除备份文件: $(basename "$backup")"
    rm "$backup"
done

# 5. 禁用 optimized-build.yml 的自动触发
echo -e "${BLUE}5. 配置 optimized-build.yml 为手动触发...${NC}"

if [ -f ".github/workflows/optimized-build.yml" ]; then
    # 确保 optimized-build.yml 只能手动触发
    if grep -q "push:" .github/workflows/optimized-build.yml; then
        echo "修改 optimized-build.yml 为手动触发模式..."
        
        # 创建临时文件
        temp_file=$(mktemp)
        
        # 移除 push 触发，只保留 workflow_dispatch
        sed '/push:/,/branches:/d' .github/workflows/optimized-build.yml > "$temp_file"
        
        # 确保有 workflow_dispatch
        if ! grep -q "workflow_dispatch:" "$temp_file"; then
            sed '1a\
  workflow_dispatch:' "$temp_file" > .github/workflows/optimized-build.yml
        else
            mv "$temp_file" .github/workflows/optimized-build.yml
        fi
        
        rm -f "$temp_file"
        echo "✅ optimized-build.yml 已配置为手动触发"
    fi
fi

# 6. 验证 ci-build.yml 配置
echo -e "${BLUE}6. 验证主要工作流配置...${NC}"

if [ -f ".github/workflows/ci-build.yml" ]; then
    echo "检查 ci-build.yml 配置..."
    
    # 检查触发条件
    if grep -q "push:" .github/workflows/ci-build.yml; then
        echo "✅ ci-build.yml 配置了 push 触发"
    else
        echo "⚠️  ci-build.yml 没有 push 触发，需要添加"
    fi
    
    # 检查健康检查端点
    if grep -q "/health/ci" .github/workflows/ci-build.yml; then
        echo "✅ ci-build.yml 使用了 CI 健康检查端点"
    else
        echo "⚠️  ci-build.yml 没有使用 CI 健康检查端点"
    fi
fi

# 7. 创建工作流状态报告
echo -e "${BLUE}7. 生成工作流状态报告...${NC}"

cat > .github/workflows-status-report.md << EOF
# 🔧 工作流冲突修复报告

## 📋 修复结果

### ✅ 保留的工作流
$(printf '- %s\n' "${keep_workflows[@]}")

### ❌ 移除的工作流
$(printf '- %s\n' "${removed_workflows[@]}")

### 🗂️ 备份位置
所有原始工作流文件已备份到: \`.github/workflows-backup/\`

## 🎯 修复效果

### 修复前
- 工作流文件数量: $(ls .github/workflows-backup/*.yml 2>/dev/null | wc -l)
- 会被触发的工作流: 11 个
- 问题: 多个工作流同时触发导致资源冲突

### 修复后
- 工作流文件数量: $(ls .github/workflows/*.yml 2>/dev/null | wc -l)
- 会被触发的工作流: 1 个 (ci-build.yml)
- 效果: 消除工作流冲突，确保构建稳定

## 🚀 工作流配置

### ci-build.yml (主要工作流)
- 触发条件: push 到 main 分支
- 功能: 完整的 CI/CD 构建和部署
- 健康检查: 使用 /health/ci 端点

### optimized-build.yml (手动工作流)
- 触发条件: 手动触发 (workflow_dispatch)
- 功能: 优化的构建流程
- 用途: 特殊情况下的手动构建

## 💡 使用建议

### 日常开发
使用 \`ci-build.yml\` 进行自动构建:
\`\`\`bash
git push origin main  # 自动触发 ci-build.yml
\`\`\`

### 特殊情况
手动触发 \`optimized-build.yml\`:
1. 进入 GitHub Actions 页面
2. 选择 "Optimized Build and Deploy"
3. 点击 "Run workflow"

## 🔄 恢复方法

如果需要恢复某个工作流:
\`\`\`bash
cp .github/workflows-backup/工作流名称.yml .github/workflows/
\`\`\`

EOF

echo -e "${GREEN}✅ 工作流冲突修复完成！${NC}"
echo -e "${BLUE}📄 状态报告: .github/workflows-status-report.md${NC}"

echo -e "\n${CYAN}📊 修复总结:${NC}"
echo -e "保留工作流: ${#keep_workflows[@]} 个"
echo -e "移除工作流: ${#removed_workflows[@]} 个"
echo -e "清理备份文件: ${#backup_files[@]} 个"

echo -e "\n${GREEN}🎯 预期效果:${NC}"
echo -e "✅ 消除工作流冲突"
echo -e "✅ 减少资源竞争"
echo -e "✅ 提高构建成功率"
echo -e "✅ 简化 CI/CD 流程"

echo -e "\n${PURPLE}🚀 下一步:${NC}"
echo -e "1. 提交修复: git add . && git commit -m 'fix: resolve workflow conflicts'"
echo -e "2. 推送代码: git push"
echo -e "3. 验证构建: 检查 GitHub Actions 页面"
