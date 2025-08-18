#!/bin/bash
# 🔍 全面的 CI/CD 构建问题诊断工具
# 暴露所有可能导致远程构建失败的问题

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 全局变量
ISSUES_FOUND=0
CRITICAL_ISSUES=0
WARNINGS=0
FIXES_APPLIED=0

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; ((WARNINGS++)); }
log_error() { echo -e "${RED}❌ $1${NC}"; ((CRITICAL_ISSUES++)); }
log_fix() { echo -e "${PURPLE}🔧 $1${NC}"; ((FIXES_APPLIED++)); }

# 创建诊断报告
REPORT_FILE="build_diagnostics_$(date +%Y%m%d_%H%M%S).md"

echo "# 🔍 CI/CD 构建问题全面诊断报告" > "$REPORT_FILE"
echo "生成时间: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo -e "${CYAN}🚀 开始全面构建诊断...${NC}"
echo "报告将保存到: $REPORT_FILE"
echo ""

# 1. 硬编码问题检测
echo -e "${BLUE}📋 1. 检测硬编码问题...${NC}"
echo "## 1. 硬编码问题检测" >> "$REPORT_FILE"

check_hardcoded_issues() {
    local issues_found=0
    
    # 检测硬编码的 IP 地址
    log_info "检查硬编码 IP 地址..."
    if grep -r --include="*.py" --include="*.yml" --include="*.yaml" -n "\b[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\b" . 2>/dev/null | grep -v ".git" | grep -v ".venv" | grep -v "127.0.0.1" | grep -v "0.0.0.0" | grep -v "os.getenv" | grep -v "# AWS VPC" | grep -v "# Docker internal" | grep -v "example.py" | head -10; then
        log_error "发现硬编码 IP 地址"
        echo "- ❌ 发现硬编码 IP 地址" >> "$REPORT_FILE"
        ((issues_found++))
    else
        log_success "未发现硬编码 IP 地址"
        echo "- ✅ 未发现硬编码 IP 地址" >> "$REPORT_FILE"
    fi
    
    # 检测硬编码的端口号
    log_info "检查硬编码端口号..."
    if grep -r --include="*.py" -n ":80[0-9][0-9]\|:90[0-9][0-9]\|:300[0-9]\|:443\|:80\b" . 2>/dev/null | grep -v ".git" | grep -v ".venv" | grep -v "localhost" | grep -v "example.com" | grep -v "APP_PORT" | grep -v "\${" | grep -v "help=" | grep -v "127.0.0.1" | grep -v "test" | grep -v "scripts/" | head -5; then
        log_warning "发现可能的硬编码端口"
        echo "- ⚠️ 发现可能的硬编码端口" >> "$REPORT_FILE"
        ((issues_found++))
    fi
    
    # 检测硬编码的文件路径
    log_info "检查硬编码文件路径..."
    if grep -r --include="*.py" -n "/opt/\|/home/\|C:\\\|/tmp/\|/var/" . 2>/dev/null | grep -v ".git" | grep -v ".venv" | grep -v "__pycache__" | grep -v "/usr/local/bin" | grep -v "/usr/bin" | grep -v "PATH=" | grep -v "PYTHONPATH" | grep -v "ExecStart=" | head -5; then
        log_warning "发现硬编码文件路径"
        echo "- ⚠️ 发现硬编码文件路径" >> "$REPORT_FILE"
        ((issues_found++))
    fi
    
    # 检测硬编码的密钥和令牌
    log_info "检查硬编码密钥..."
    if grep -r --include="*.py" --include="*.yml" -i -n "token.*=.*['\"][a-zA-Z0-9]\{20,\}\|key.*=.*['\"][a-zA-Z0-9]\{20,\}\|secret.*=.*['\"][a-zA-Z0-9]\{20,\}" . 2>/dev/null | grep -v ".git" | head -3; then
        log_error "发现可能的硬编码密钥"
        echo "- ❌ 发现可能的硬编码密钥" >> "$REPORT_FILE"
        ((issues_found++))
    fi
    
    return $issues_found
}

check_hardcoded_issues
echo "" >> "$REPORT_FILE"

# 2. 环境依赖问题
echo -e "${BLUE}📋 2. 检测环境依赖问题...${NC}"
echo "## 2. 环境依赖问题" >> "$REPORT_FILE"

check_environment_issues() {
    # 检查 Python 版本兼容性
    log_info "检查 Python 版本兼容性..."
    if grep -r --include="*.py" -n "python_requires\|sys.version_info" . 2>/dev/null | head -3; then
        log_success "发现 Python 版本检查"
        echo "- ✅ 发现 Python 版本检查" >> "$REPORT_FILE"
    else
        log_warning "未发现 Python 版本检查"
        echo "- ⚠️ 未发现 Python 版本检查" >> "$REPORT_FILE"
    fi
    
    # 检查操作系统特定代码
    log_info "检查操作系统特定代码..."
    if grep -r --include="*.py" -n "platform\|os.name\|sys.platform" . 2>/dev/null | head -3; then
        log_warning "发现操作系统特定代码"
        echo "- ⚠️ 发现操作系统特定代码，可能影响跨平台构建" >> "$REPORT_FILE"
    fi
    
    # 检查环境变量使用
    log_info "检查环境变量使用..."
    local env_vars=$(grep -r --include="*.py" -n "os.environ\|getenv" . 2>/dev/null | wc -l)
    if [ "$env_vars" -gt 0 ]; then
        log_success "发现 $env_vars 处环境变量使用"
        echo "- ✅ 发现 $env_vars 处环境变量使用" >> "$REPORT_FILE"
    fi
}

check_environment_issues
echo "" >> "$REPORT_FILE"

# 3. Docker 构建问题
echo -e "${BLUE}📋 3. 检测 Docker 构建问题...${NC}"
echo "## 3. Docker 构建问题" >> "$REPORT_FILE"

check_docker_issues() {
    # 检查 Dockerfile 存在性和语法
    log_info "检查 Dockerfile..."
    for dockerfile in Dockerfile Dockerfile.* */Dockerfile; do
        if [ -f "$dockerfile" ]; then
            log_success "发现 $dockerfile"
            echo "- ✅ 发现 $dockerfile" >> "$REPORT_FILE"
            
            # 检查 Dockerfile 最佳实践
            if grep -q "apt-get update.*apt-get install" "$dockerfile"; then
                log_warning "$dockerfile: 建议合并 apt-get 命令"
                echo "  - ⚠️ 建议合并 apt-get 命令" >> "$REPORT_FILE"
            fi
            
            if ! grep -q "rm -rf /var/lib/apt/lists" "$dockerfile"; then
                log_warning "$dockerfile: 建议清理 apt 缓存"
                echo "  - ⚠️ 建议清理 apt 缓存" >> "$REPORT_FILE"
            fi
            
            if ! grep -q "HEALTHCHECK" "$dockerfile"; then
                log_warning "$dockerfile: 缺少健康检查"
                echo "  - ⚠️ 缺少健康检查" >> "$REPORT_FILE"
            fi
        fi
    done
    
    # 检查 .dockerignore
    if [ -f ".dockerignore" ]; then
        log_success "发现 .dockerignore"
        echo "- ✅ 发现 .dockerignore" >> "$REPORT_FILE"
        
        local size=$(du -sh . 2>/dev/null | cut -f1)
        log_info "当前目录大小: $size"
        echo "  - 当前目录大小: $size" >> "$REPORT_FILE"
    else
        log_error "缺少 .dockerignore 文件"
        echo "- ❌ 缺少 .dockerignore 文件" >> "$REPORT_FILE"
    fi
}

check_docker_issues
echo "" >> "$REPORT_FILE"

# 4. 依赖包问题
echo -e "${BLUE}📋 4. 检测依赖包问题...${NC}"
echo "## 4. 依赖包问题" >> "$REPORT_FILE"

check_dependency_issues() {
    # 检查 requirements.txt
    if [ -f "requirements.txt" ]; then
        log_success "发现 requirements.txt"
        echo "- ✅ 发现 requirements.txt" >> "$REPORT_FILE"
        
        # 检查版本固定
        local unpinned=$(grep -v "==" requirements.txt | grep -v "^#" | grep -v "^$" | wc -l)
        if [ "$unpinned" -gt 0 ]; then
            log_warning "发现 $unpinned 个未固定版本的包"
            echo "  - ⚠️ 发现 $unpinned 个未固定版本的包" >> "$REPORT_FILE"
        fi
        
        # 检查已知问题包
        if grep -q "tensorflow\|torch\|numpy.*1\..*\|scipy.*1\." requirements.txt; then
            log_warning "发现可能导致构建问题的大型包"
            echo "  - ⚠️ 发现可能导致构建问题的大型包" >> "$REPORT_FILE"
        fi
    else
        log_error "缺少 requirements.txt"
        echo "- ❌ 缺少 requirements.txt" >> "$REPORT_FILE"
    fi
    
    # 检查 Python 导入
    log_info "检查 Python 导入问题..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import app
    print('✅ app 模块导入成功')
except Exception as e:
    print(f'❌ app 模块导入失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "Python 导入检查通过"
        echo "- ✅ Python 导入检查通过" >> "$REPORT_FILE"
    else
        log_error "Python 导入检查失败"
        echo "- ❌ Python 导入检查失败" >> "$REPORT_FILE"
    fi
}

check_dependency_issues
echo "" >> "$REPORT_FILE"

# 5. 代码质量问题
echo -e "${BLUE}📋 5. 检测代码质量问题...${NC}"
echo "## 5. 代码质量问题" >> "$REPORT_FILE"

check_code_quality() {
    # 检查 Python 语法
    log_info "检查 Python 语法..."
    local syntax_errors=0
    for py_file in $(find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | head -20); do
        if ! python3 -m py_compile "$py_file" 2>/dev/null; then
            log_error "语法错误: $py_file"
            echo "  - ❌ 语法错误: $py_file" >> "$REPORT_FILE"
            ((syntax_errors++))
        fi
    done
    
    if [ "$syntax_errors" -eq 0 ]; then
        log_success "Python 语法检查通过"
        echo "- ✅ Python 语法检查通过" >> "$REPORT_FILE"
    fi
    
    # 检查代码格式
    if command -v black >/dev/null 2>&1; then
        log_info "检查代码格式..."
        if black --check --diff . >/dev/null 2>&1; then
            log_success "代码格式检查通过"
            echo "- ✅ 代码格式检查通过" >> "$REPORT_FILE"
        else
            log_warning "代码格式需要修复"
            echo "- ⚠️ 代码格式需要修复" >> "$REPORT_FILE"
        fi
    fi
}

check_code_quality
echo "" >> "$REPORT_FILE"

# 6. CI/CD 配置问题
echo -e "${BLUE}📋 6. 检测 CI/CD 配置问题...${NC}"
echo "## 6. CI/CD 配置问题" >> "$REPORT_FILE"

check_cicd_config() {
    # 检查 GitHub Actions 工作流
    if [ -d ".github/workflows" ]; then
        log_success "发现 GitHub Actions 工作流"
        echo "- ✅ 发现 GitHub Actions 工作流" >> "$REPORT_FILE"
        
        # 检查 YAML 语法
        for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
            if [ -f "$workflow" ]; then
                if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
                    log_success "YAML 语法正确: $(basename $workflow)"
                    echo "  - ✅ YAML 语法正确: $(basename $workflow)" >> "$REPORT_FILE"
                else
                    log_error "YAML 语法错误: $(basename $workflow)"
                    echo "  - ❌ YAML 语法错误: $(basename $workflow)" >> "$REPORT_FILE"
                fi
            fi
        done
    fi
    
    # 检查 secrets 使用
    log_info "检查 secrets 使用..."
    local secrets_count=$(grep -r "secrets\." .github/workflows/ 2>/dev/null | wc -l)
    if [ "$secrets_count" -gt 0 ]; then
        log_success "发现 $secrets_count 处 secrets 使用"
        echo "- ✅ 发现 $secrets_count 处 secrets 使用" >> "$REPORT_FILE"
        
        # 列出所有使用的 secrets
        grep -r "secrets\." .github/workflows/ 2>/dev/null | sed 's/.*secrets\.\([A-Z_]*\).*/\1/' | sort -u | while read secret; do
            echo "  - Secret: $secret" >> "$REPORT_FILE"
        done
    fi
}

check_cicd_config
echo "" >> "$REPORT_FILE"

# 生成修复建议
echo -e "${BLUE}📋 7. 生成修复建议...${NC}"
echo "## 7. 自动修复建议" >> "$REPORT_FILE"

generate_fixes() {
    echo "### 立即可执行的修复:" >> "$REPORT_FILE"
    
    # 创建 .dockerignore 如果不存在
    if [ ! -f ".dockerignore" ]; then
        log_fix "创建 .dockerignore 文件"
        cat > .dockerignore << 'EOF'
.git
.venv
__pycache__
*.pyc
.pytest_cache
.coverage
htmlcov
.tox
tests/
docs/
*.md
!requirements*.txt
.env*
*.log
EOF
        echo "- 🔧 已创建 .dockerignore 文件" >> "$REPORT_FILE"
    fi
    
    # 修复代码格式
    if command -v black >/dev/null 2>&1; then
        log_fix "修复代码格式"
        black . >/dev/null 2>&1 || true
        echo "- 🔧 已修复代码格式" >> "$REPORT_FILE"
    fi
    
    echo "" >> "$REPORT_FILE"
    echo "### 需要手动处理的问题:" >> "$REPORT_FILE"
    echo "- 检查并移除硬编码的 IP 地址和端口" >> "$REPORT_FILE"
    echo "- 将硬编码值移动到环境变量" >> "$REPORT_FILE"
    echo "- 确保所有 GitHub Secrets 正确配置" >> "$REPORT_FILE"
    echo "- 优化 Dockerfile 以减少构建时间" >> "$REPORT_FILE"
}

generate_fixes

# 最终报告
echo "" >> "$REPORT_FILE"
echo "## 8. 诊断总结" >> "$REPORT_FILE"
echo "- 发现的问题总数: $((CRITICAL_ISSUES + WARNINGS))" >> "$REPORT_FILE"
echo "- 严重问题: $CRITICAL_ISSUES" >> "$REPORT_FILE"
echo "- 警告: $WARNINGS" >> "$REPORT_FILE"
echo "- 自动修复: $FIXES_APPLIED" >> "$REPORT_FILE"

echo ""
echo -e "${CYAN}🎉 诊断完成！${NC}"
echo -e "${BLUE}📊 总结:${NC}"
echo -e "  严重问题: ${RED}$CRITICAL_ISSUES${NC}"
echo -e "  警告: ${YELLOW}$WARNINGS${NC}"
echo -e "  自动修复: ${PURPLE}$FIXES_APPLIED${NC}"
echo ""
echo -e "${GREEN}📄 详细报告已保存到: $REPORT_FILE${NC}"

# 如果有严重问题，返回错误码
if [ "$CRITICAL_ISSUES" -gt 0 ]; then
    echo -e "${RED}⚠️  发现严重问题，建议修复后再进行构建${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 未发现严重问题，可以尝试构建${NC}"
    exit 0
fi
