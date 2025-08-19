#!/bin/bash
# 📈 持续质量改进脚本
# 自动化质量分析和改进建议

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}📈 启动持续质量改进分析...${NC}"

# 创建质量报告目录
mkdir -p quality-reports

# 获取当前时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}📊 收集质量数据...${NC}"

# 1. 运行完整测试套件并收集覆盖率数据
echo -e "${PURPLE}🧪 运行测试套件...${NC}"
python -m pytest tests/priority/ \
  --cov=app \
  --cov-report=xml:quality-reports/coverage-${TIMESTAMP}.xml \
  --cov-report=html:quality-reports/coverage-html-${TIMESTAMP} \
  --cov-report=term \
  --tb=short \
  -v > quality-reports/test-${TIMESTAMP}.log 2>&1 || echo "⚠️  测试执行完成（可能有失败）"

# 2. 运行性能基准测试
echo -e "${PURPLE}🚀 运行性能基准测试...${NC}"
if [ -f "tests/performance/test_performance_benchmarks.py" ]; then
  pip install pytest-benchmark > /dev/null 2>&1 || echo "安装 pytest-benchmark..."
  python -m pytest tests/performance/test_performance_benchmarks.py \
    --benchmark-only \
    --benchmark-json=quality-reports/benchmark-${TIMESTAMP}.json \
    --benchmark-sort=mean \
    -v > quality-reports/performance-${TIMESTAMP}.log 2>&1 || echo "⚠️  性能测试完成（可能有失败）"
else
  echo "ℹ️  未找到性能测试文件，跳过性能分析"
fi

# 3. 代码质量检查
echo -e "${PURPLE}🔍 运行代码质量检查...${NC}"

# 检查代码复杂度
if command -v radon &> /dev/null; then
  echo "📊 分析代码复杂度..."
  radon cc app/ --json > quality-reports/complexity-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  复杂度分析失败"
else
  echo "ℹ️  radon 未安装，跳过复杂度分析"
fi

# 检查代码重复
if command -v pylint &> /dev/null; then
  echo "🔍 检查代码质量..."
  pylint app/ --output-format=json > quality-reports/pylint-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  代码质量检查完成"
else
  echo "ℹ️  pylint 未安装，跳过代码质量检查"
fi

# 4. 安全扫描
echo -e "${PURPLE}🔒 运行安全扫描...${NC}"

# 依赖漏洞扫描
if command -v safety &> /dev/null; then
  echo "🛡️  扫描依赖漏洞..."
  safety check --json > quality-reports/safety-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  发现安全漏洞"
else
  pip install safety > /dev/null 2>&1
  safety check --json > quality-reports/safety-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  发现安全漏洞"
fi

# 代码安全扫描
if command -v bandit &> /dev/null; then
  echo "🔍 扫描代码安全问题..."
  bandit -r app/ -f json > quality-reports/bandit-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  发现代码安全问题"
else
  pip install bandit > /dev/null 2>&1
  bandit -r app/ -f json > quality-reports/bandit-${TIMESTAMP}.json 2>/dev/null || echo "⚠️  发现代码安全问题"
fi

# 5. 运行质量分析器
echo -e "${BLUE}📈 运行质量分析器...${NC}"
python scripts/quality-improvement-analyzer.py

# 6. 生成改进建议
echo -e "${BLUE}💡 生成改进建议...${NC}"

# 检查最新的质量报告
if [ -f "quality-reports/quality-report-latest.md" ]; then
  echo -e "${GREEN}📋 质量报告已生成${NC}"
  
  # 显示关键指标
  echo -e "\n${CYAN}📊 关键质量指标:${NC}"
  
  # 提取覆盖率信息
  if [ -f "quality-reports/coverage-${TIMESTAMP}.xml" ]; then
    COVERAGE=$(python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('quality-reports/coverage-${TIMESTAMP}.xml')
    root = tree.getroot()
    coverage = float(root.attrib['line-rate']) * 100
    print(f'{coverage:.1f}')
except:
    print('N/A')
")
    echo -e "  📊 整体覆盖率: ${COVERAGE}%"
  fi
  
  # 检查测试结果
  if grep -q "FAILED" quality-reports/test-${TIMESTAMP}.log 2>/dev/null; then
    FAILED_COUNT=$(grep -c "FAILED" quality-reports/test-${TIMESTAMP}.log 2>/dev/null || echo "0")
    echo -e "  ❌ 失败测试: ${FAILED_COUNT} 个"
  else
    echo -e "  ✅ 测试状态: 全部通过"
  fi
  
  # 检查性能状态
  if [ -f "quality-reports/benchmark-${TIMESTAMP}.json" ]; then
    echo -e "  🚀 性能测试: 已完成"
  else
    echo -e "  ⚠️  性能测试: 未运行"
  fi
  
  # 显示改进建议摘要
  echo -e "\n${CYAN}💡 改进建议摘要:${NC}"
  if grep -q "🔴" quality-reports/quality-report-latest.md; then
    echo -e "  🔴 发现严重问题，需要立即处理"
  elif grep -q "🟡" quality-reports/quality-report-latest.md; then
    echo -e "  🟡 发现改进机会，建议及时处理"
  else
    echo -e "  🟢 质量状态良好"
  fi
  
  echo -e "\n${BLUE}📄 查看完整报告: quality-reports/quality-report-latest.md${NC}"
  
else
  echo -e "${RED}❌ 质量报告生成失败${NC}"
  exit 1
fi

# 7. 自动化改进建议
echo -e "${BLUE}🤖 生成自动化改进脚本...${NC}"

cat > quality-reports/auto-improvement-${TIMESTAMP}.sh << 'EOF'
#!/bin/bash
# 🤖 自动化质量改进脚本
# 基于分析结果的自动化改进建议

echo "🤖 执行自动化质量改进..."

# 1. 自动修复代码格式问题
if command -v black &> /dev/null; then
  echo "🎨 自动修复代码格式..."
  black app/ tests/
fi

if command -v isort &> /dev/null; then
  echo "📦 自动修复导入排序..."
  isort app/ tests/
fi

# 2. 自动移除未使用的导入
if command -v autoflake &> /dev/null; then
  echo "🧹 移除未使用的导入..."
  autoflake --remove-all-unused-imports --recursive --in-place app/ tests/
fi

# 3. 自动生成缺失的测试模板
echo "📝 生成缺失的测试模板..."

# 检查是否有未测试的模块
for py_file in app/*.py; do
  if [ -f "$py_file" ] && [ "$(basename "$py_file")" != "__init__.py" ]; then
    module_name=$(basename "$py_file" .py)
    test_file="tests/priority/auto_generated/test_${module_name}_auto.py"
    
    if [ ! -f "$test_file" ]; then
      echo "生成 $module_name 的测试模板..."
      mkdir -p tests/priority/auto_generated
      
      cat > "$test_file" << TEMPLATE
"""
🤖 自动生成的测试模板 - ${module_name}
请根据实际需求完善测试用例
"""
import pytest
from unittest.mock import patch, MagicMock

from app.${module_name} import *


class Test${module_name^}:
    """${module_name} 模块测试"""
    
    def test_placeholder(self):
        """占位测试 - 请替换为实际测试"""
        # TODO: 添加实际测试用例
        assert True, "请添加实际测试用例"
TEMPLATE
    fi
  fi
done

echo "✅ 自动化改进完成"
echo "📝 请检查生成的测试模板并完善测试用例"
EOF

chmod +x quality-reports/auto-improvement-${TIMESTAMP}.sh

# 8. 生成质量趋势图表（如果有历史数据）
echo -e "${BLUE}📈 生成质量趋势图表...${NC}"

python -c "
import os
import json
import matplotlib.pyplot as plt
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    
    reports_dir = Path('quality-reports')
    coverage_files = sorted(reports_dir.glob('coverage-*.xml'))
    
    if len(coverage_files) >= 2:
        dates = []
        coverages = []
        
        for file in coverage_files[-10:]:  # 最近10次
            try:
                tree = ET.parse(file)
                root = tree.getroot()
                coverage = float(root.attrib['line-rate']) * 100
                
                timestamp = file.stem.split('-')[-1]
                dates.append(timestamp)
                coverages.append(coverage)
            except:
                continue
        
        if dates and coverages:
            plt.figure(figsize=(10, 6))
            plt.plot(dates, coverages, marker='o', linewidth=2, markersize=6)
            plt.title('代码覆盖率趋势', fontsize=16)
            plt.xlabel('时间', fontsize=12)
            plt.ylabel('覆盖率 (%)', fontsize=12)
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig('quality-reports/coverage-trend.png', dpi=150, bbox_inches='tight')
            print('📊 覆盖率趋势图已生成: quality-reports/coverage-trend.png')
        else:
            print('ℹ️  数据不足，无法生成趋势图')
    else:
        print('ℹ️  历史数据不足，无法生成趋势图')
        
except ImportError:
    print('ℹ️  matplotlib 未安装，跳过图表生成')
except Exception as e:
    print(f'⚠️  图表生成失败: {e}')
" 2>/dev/null || echo "ℹ️  跳过图表生成"

# 9. 总结和下一步建议
echo -e "\n${GREEN}🎉 质量改进分析完成！${NC}"

echo -e "\n${CYAN}📋 生成的文件:${NC}"
echo -e "  📊 覆盖率报告: quality-reports/coverage-html-${TIMESTAMP}/index.html"
echo -e "  📈 质量分析报告: quality-reports/quality-report-latest.md"
echo -e "  🤖 自动改进脚本: quality-reports/auto-improvement-${TIMESTAMP}.sh"

if [ -f "quality-reports/coverage-trend.png" ]; then
  echo -e "  📈 覆盖率趋势图: quality-reports/coverage-trend.png"
fi

echo -e "\n${CYAN}🚀 下一步建议:${NC}"
echo -e "  1. 查看质量报告: cat quality-reports/quality-report-latest.md"
echo -e "  2. 运行自动改进: ./quality-reports/auto-improvement-${TIMESTAMP}.sh"
echo -e "  3. 修复发现的问题"
echo -e "  4. 重新运行测试验证改进效果"

echo -e "\n${BLUE}💡 定期运行此脚本以持续改进代码质量！${NC}"
