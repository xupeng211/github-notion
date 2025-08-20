#!/bin/bash
# 🔍 Docker构建上下文大小计算脚本
# 使用tar + exclude模拟Docker构建上下文，计算压缩后大小

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔍 Docker构建上下文大小分析${NC}"
echo "=================================================="

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查.dockerignore文件
if [[ ! -f .dockerignore ]]; then
    echo -e "${RED}❌ .dockerignore文件不存在${NC}"
    exit 1
fi

echo -e "${BLUE}📋 .dockerignore配置:${NC}"
echo "排除规则数量: $(grep -v '^#' .dockerignore | grep -v '^$' | wc -l)"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 读取.dockerignore并转换为tar exclude格式
EXCLUDE_FILE="$TEMP_DIR/excludes.txt"
echo -e "${BLUE}🔧 处理.dockerignore规则...${NC}"

# 转换.dockerignore规则为tar exclude格式
while IFS= read -r line; do
    # 跳过注释和空行
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
        continue
    fi
    
    # 移除前后空格
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # 转换Docker ignore规则为tar exclude格式
    if [[ "$line" == *"/**" ]]; then
        # 处理 .git/** 格式
        echo "--exclude=${line%/**}" >> "$EXCLUDE_FILE"
        echo "--exclude=${line}" >> "$EXCLUDE_FILE"
    elif [[ "$line" == *"/" ]]; then
        # 目录格式，移除尾部斜杠
        echo "--exclude=${line%/}" >> "$EXCLUDE_FILE"
    else
        # 文件或通配符格式
        echo "--exclude=$line" >> "$EXCLUDE_FILE"
    fi
done < .dockerignore

echo "生成的exclude规则数量: $(wc -l < "$EXCLUDE_FILE")"

# 计算原始目录大小
echo -e "\n${BLUE}📊 目录大小分析:${NC}"
ORIGINAL_SIZE=$(du -sb . | cut -f1)
echo "原始目录大小: $(python3 "$SCRIPT_DIR/pretty_size.py" $ORIGINAL_SIZE)"

# 使用tar模拟Docker构建上下文
echo -e "\n${BLUE}🐳 模拟Docker构建上下文...${NC}"
TAR_FILE="$TEMP_DIR/context.tar"

# 执行tar命令，使用.dockerignore规则
if tar -cf "$TAR_FILE" $(cat "$EXCLUDE_FILE") . 2>/dev/null; then
    TAR_SIZE=$(stat -c%s "$TAR_FILE")
    echo "构建上下文大小(未压缩): $(python3 "$SCRIPT_DIR/pretty_size.py" $TAR_SIZE)"
    
    # 压缩tar文件模拟网络传输
    gzip "$TAR_FILE"
    COMPRESSED_SIZE=$(stat -c%s "$TAR_FILE.gz")
    echo "构建上下文大小(压缩后): $(python3 "$SCRIPT_DIR/pretty_size.py" $COMPRESSED_SIZE)"
    
    # 计算压缩比（使用Python避免bc依赖）
    COMPRESSION_RATIO=$(python3 -c "print(f'{$COMPRESSED_SIZE * 100 / $TAR_SIZE:.1f}')" 2>/dev/null || echo "0.0")
    echo "压缩比: ${COMPRESSION_RATIO}%"

    # 计算减少比例（使用Python避免bc依赖）
    REDUCTION_RATIO=$(python3 -c "print(f'{($ORIGINAL_SIZE - $TAR_SIZE) * 100 / $ORIGINAL_SIZE:.1f}')" 2>/dev/null || echo "0.0")
    echo "上下文减少: ${REDUCTION_RATIO}%"
    
else
    echo -e "${RED}❌ tar命令执行失败${NC}"
    exit 1
fi

# 检查大小阈值
echo -e "\n${BLUE}🚦 大小检查:${NC}"
THRESHOLD_MB=500
THRESHOLD_BYTES=$((THRESHOLD_MB * 1024 * 1024))

if [[ $COMPRESSED_SIZE -gt $THRESHOLD_BYTES ]]; then
    echo -e "${RED}❌ 构建上下文过大: $(python3 "$SCRIPT_DIR/pretty_size.py" $COMPRESSED_SIZE) > ${THRESHOLD_MB}MB${NC}"
    echo -e "${YELLOW}💡 建议优化:${NC}"
    echo "1. 检查.dockerignore是否遗漏大文件"
    echo "2. 清理不必要的缓存和临时文件"
    echo "3. 考虑使用多阶段构建"
    exit 1
else
    echo -e "${GREEN}✅ 构建上下文大小合理: $(python3 "$SCRIPT_DIR/pretty_size.py" $COMPRESSED_SIZE) ≤ ${THRESHOLD_MB}MB${NC}"
fi

# 显示最大的文件/目录
echo -e "\n${BLUE}📈 最大的文件和目录:${NC}"
echo "前10个最大文件:"
find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './.cleanup-backup/*' \
    -exec du -h {} + 2>/dev/null | sort -hr | head -10 | while read size file; do
    echo "  $size  $file"
done

echo -e "\n前5个最大目录:"
du -h --max-depth=1 . 2>/dev/null | sort -hr | head -6 | tail -5 | while read size dir; do
    echo "  $size  $dir"
done

echo -e "\n${GREEN}✅ 构建上下文分析完成${NC}"
