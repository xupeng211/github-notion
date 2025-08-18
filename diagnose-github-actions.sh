#!/bin/bash
# 🔍 诊断 GitHub Actions 问题
# 分析 GitHub Actions 环境中的具体问题

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 诊断 GitHub Actions 问题...${NC}"

# 创建诊断目录
mkdir -p github-actions-diagnosis

# 1. 检查工作流配置
echo -e "${BLUE}1. 检查工作流配置...${NC}"

workflow_file=".github/workflows/ci-build.yml"
diagnosis_log="github-actions-diagnosis/workflow-diagnosis.log"

echo "=== 工作流配置诊断 ===" > "$diagnosis_log"
echo "工作流文件: $workflow_file" >> "$diagnosis_log"
echo "检查时间: $(date)" >> "$diagnosis_log"
echo "" >> "$diagnosis_log"

# 检查工作流文件是否存在
if [ -f "$workflow_file" ]; then
    echo "✅ 工作流文件存在" >> "$diagnosis_log"
    echo "✅ 工作流文件存在"
    
    # 检查语法
    if python3 -c "import yaml; yaml.safe_load(open('$workflow_file'))" 2>/dev/null; then
        echo "✅ YAML 语法正确" >> "$diagnosis_log"
        echo "✅ YAML 语法正确"
    else
        echo "❌ YAML 语法错误" >> "$diagnosis_log"
        echo "❌ YAML 语法错误"
        python3 -c "import yaml; yaml.safe_load(open('$workflow_file'))" >> "$diagnosis_log" 2>&1 || true
    fi
    
    # 检查关键配置
    echo "=== 关键配置检查 ===" >> "$diagnosis_log"
    
    # 检查 Dockerfile 路径
    if grep -q "Dockerfile.github" "$workflow_file"; then
        echo "✅ 使用 Dockerfile.github" >> "$diagnosis_log"
        echo "✅ 使用 Dockerfile.github"
    else
        echo "⚠️  未明确指定 Dockerfile.github" >> "$diagnosis_log"
        echo "⚠️  未明确指定 Dockerfile.github"
    fi
    
    # 检查镜像推送配置
    if grep -q "ghcr.io" "$workflow_file"; then
        echo "✅ 配置了 GitHub Container Registry" >> "$diagnosis_log"
        echo "✅ 配置了 GitHub Container Registry"
    else
        echo "❌ 未配置 GitHub Container Registry" >> "$diagnosis_log"
        echo "❌ 未配置 GitHub Container Registry"
    fi
    
    # 检查权限配置
    if grep -q "permissions:" "$workflow_file"; then
        echo "✅ 配置了权限" >> "$diagnosis_log"
        echo "✅ 配置了权限"
        
        # 检查具体权限
        if grep -A 10 "permissions:" "$workflow_file" | grep -q "packages: write"; then
            echo "✅ 配置了 packages: write 权限" >> "$diagnosis_log"
            echo "✅ 配置了 packages: write 权限"
        else
            echo "❌ 缺少 packages: write 权限" >> "$diagnosis_log"
            echo "❌ 缺少 packages: write 权限"
        fi
    else
        echo "❌ 未配置权限" >> "$diagnosis_log"
        echo "❌ 未配置权限"
    fi
    
else
    echo "❌ 工作流文件不存在" >> "$diagnosis_log"
    echo "❌ 工作流文件不存在"
fi

# 2. 检查 Dockerfile.github
echo -e "\n${BLUE}2. 检查 Dockerfile.github...${NC}"

dockerfile_log="github-actions-diagnosis/dockerfile-diagnosis.log"
echo "=== Dockerfile.github 诊断 ===" > "$dockerfile_log"

if [ -f "Dockerfile.github" ]; then
    echo "✅ Dockerfile.github 存在" >> "$dockerfile_log"
    echo "✅ Dockerfile.github 存在"
    
    # 检查基础镜像
    base_image=$(grep "^FROM" Dockerfile.github | head -1 | awk '{print $2}')
    echo "基础镜像: $base_image" >> "$dockerfile_log"
    echo "基础镜像: $base_image"
    
    # 检查 Python 版本
    if echo "$base_image" | grep -q "python:"; then
        python_version=$(echo "$base_image" | grep -o "python:[^-]*" | cut -d: -f2)
        echo "Python 版本: $python_version" >> "$dockerfile_log"
        echo "Python 版本: $python_version"
    fi
    
    # 检查工作目录
    if grep -q "WORKDIR" Dockerfile.github; then
        workdir=$(grep "WORKDIR" Dockerfile.github | awk '{print $2}')
        echo "工作目录: $workdir" >> "$dockerfile_log"
        echo "工作目录: $workdir"
    fi
    
    # 检查依赖安装
    if grep -q "requirements.txt" Dockerfile.github; then
        echo "✅ 安装 requirements.txt" >> "$dockerfile_log"
        echo "✅ 安装 requirements.txt"
    else
        echo "⚠️  未安装 requirements.txt" >> "$dockerfile_log"
        echo "⚠️  未安装 requirements.txt"
    fi
    
    # 检查端口暴露
    if grep -q "EXPOSE" Dockerfile.github; then
        port=$(grep "EXPOSE" Dockerfile.github | awk '{print $2}')
        echo "暴露端口: $port" >> "$dockerfile_log"
        echo "暴露端口: $port"
    else
        echo "⚠️  未暴露端口" >> "$dockerfile_log"
        echo "⚠️  未暴露端口"
    fi
    
else
    echo "❌ Dockerfile.github 不存在" >> "$dockerfile_log"
    echo "❌ Dockerfile.github 不存在"
fi

# 3. 检查可能的 GitHub Actions 问题
echo -e "\n${BLUE}3. 检查可能的 GitHub Actions 问题...${NC}"

issues_log="github-actions-diagnosis/potential-issues.log"
echo "=== 潜在问题分析 ===" > "$issues_log"

# 检查仓库设置
echo "检查仓库设置..." >> "$issues_log"
echo "检查仓库设置..."

# 检查 GitHub Container Registry 权限
echo "1. GitHub Container Registry 权限问题" >> "$issues_log"
echo "   - 需要在仓库设置中启用 GitHub Packages" >> "$issues_log"
echo "   - 需要 GITHUB_TOKEN 有 packages:write 权限" >> "$issues_log"
echo "   - 检查工作流权限设置" >> "$issues_log"

# 检查网络问题
echo "2. 网络连接问题" >> "$issues_log"
echo "   - GitHub Actions 环境网络限制" >> "$issues_log"
echo "   - 基础镜像下载失败" >> "$issues_log"
echo "   - pip 包下载超时" >> "$issues_log"

# 检查资源限制
echo "3. 资源限制问题" >> "$issues_log"
echo "   - GitHub Actions 内存限制" >> "$issues_log"
echo "   - 构建时间超时" >> "$issues_log"
echo "   - 磁盘空间不足" >> "$issues_log"

# 检查环境差异
echo "4. 环境差异问题" >> "$issues_log"
echo "   - 本地 Docker 版本 vs GitHub Actions Docker 版本" >> "$issues_log"
echo "   - 平台差异 (linux/amd64 vs linux/arm64)" >> "$issues_log"
echo "   - 环境变量差异" >> "$issues_log"

# 4. 生成修复建议
echo -e "\n${BLUE}4. 生成修复建议...${NC}"

suggestions_log="github-actions-diagnosis/fix-suggestions.log"
echo "=== 修复建议 ===" > "$suggestions_log"

echo "基于诊断结果的修复建议:" >> "$suggestions_log"
echo ""

# 权限相关修复
echo "1. 权限配置修复:" >> "$suggestions_log"
echo "   - 确保工作流有 packages: write 权限" >> "$suggestions_log"
echo "   - 检查仓库设置 > Actions > General > Workflow permissions" >> "$suggestions_log"
echo "   - 启用 'Read and write permissions'" >> "$suggestions_log"
echo "" >> "$suggestions_log"

# 网络相关修复
echo "2. 网络问题修复:" >> "$suggestions_log"
echo "   - 添加重试机制" >> "$suggestions_log"
echo "   - 使用更稳定的基础镜像" >> "$suggestions_log"
echo "   - 配置 pip 镜像源" >> "$suggestions_log"
echo "" >> "$suggestions_log"

# 构建优化
echo "3. 构建优化:" >> "$suggestions_log"
echo "   - 使用多阶段构建减少镜像大小" >> "$suggestions_log"
echo "   - 添加构建缓存" >> "$suggestions_log"
echo "   - 优化依赖安装顺序" >> "$suggestions_log"
echo "" >> "$suggestions_log"

# 调试建议
echo "4. 调试建议:" >> "$suggestions_log"
echo "   - 添加详细的构建日志" >> "$suggestions_log"
echo "   - 在工作流中添加调试步骤" >> "$suggestions_log"
echo "   - 使用 tmate 进行远程调试" >> "$suggestions_log"

# 5. 生成综合报告
echo -e "\n${BLUE}5. 生成综合报告...${NC}"

cat > github-actions-diagnosis/comprehensive-diagnosis.md << 'EOF'
# 🔍 GitHub Actions 问题诊断报告

## 📋 诊断概览

### 🎯 问题现象
- 本地构建: ✅ 成功
- GitHub Actions 构建: ❌ 失败
- 问题类型: 环境差异问题

### 🔍 诊断结果
详细诊断结果请查看:
- `workflow-diagnosis.log` - 工作流配置诊断
- `dockerfile-diagnosis.log` - Dockerfile 诊断
- `potential-issues.log` - 潜在问题分析
- `fix-suggestions.log` - 修复建议

## 🎯 最可能的问题

### 1. GitHub Container Registry 权限问题
**症状**: 构建成功但推送失败
**原因**: 缺少 packages:write 权限
**修复**: 配置正确的工作流权限

### 2. 网络连接问题
**症状**: 依赖下载失败或超时
**原因**: GitHub Actions 环境网络限制
**修复**: 添加重试机制和镜像源

### 3. 环境差异问题
**症状**: 本地成功但远程失败
**原因**: Docker 版本或平台差异
**修复**: 统一环境配置

## 💡 立即修复建议

### 第一步: 检查权限配置
1. 进入仓库设置 > Actions > General
2. 确保 Workflow permissions 设置为 "Read and write permissions"
3. 检查工作流文件中的 permissions 配置

### 第二步: 优化工作流配置
1. 添加详细的错误日志
2. 配置重试机制
3. 使用稳定的基础镜像

### 第三步: 添加调试信息
1. 在工作流中添加环境信息输出
2. 添加构建步骤的详细日志
3. 配置失败时的调试模式

## 🚀 下一步行动

1. 实施权限修复
2. 优化工作流配置
3. 添加调试信息
4. 重新测试构建

EOF

echo -e "${GREEN}✅ GitHub Actions 问题诊断完成！${NC}"
echo -e "${BLUE}📄 综合报告: github-actions-diagnosis/comprehensive-diagnosis.md${NC}"
echo -e "${YELLOW}📁 详细诊断保存在: github-actions-diagnosis/${NC}"

# 显示关键发现
echo -e "\n${CYAN}🎯 关键发现总结:${NC}"

# 检查权限配置
if grep -q "packages: write" "$workflow_file" 2>/dev/null; then
    echo -e "${GREEN}✅ 工作流配置了 packages: write 权限${NC}"
else
    echo -e "${RED}❌ 工作流缺少 packages: write 权限${NC}"
    echo -e "${YELLOW}💡 这可能是导致构建失败的主要原因${NC}"
fi

# 检查 Dockerfile
if [ -f "Dockerfile.github" ]; then
    echo -e "${GREEN}✅ Dockerfile.github 存在${NC}"
else
    echo -e "${RED}❌ Dockerfile.github 不存在${NC}"
fi

echo -e "\n${PURPLE}🔧 建议立即检查 GitHub 仓库的 Actions 权限设置${NC}"
