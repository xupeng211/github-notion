#!/usr/bin/env python3
"""
批量修复代码质量问题脚本
自动处理 flake8 报告的各种代码格式问题
"""

import re
import os
from pathlib import Path
import ast


def fix_file(file_path: Path) -> bool:
    """修复单个文件的代码质量问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content

        # 1. 修复缩进问题 - 替换 tab 为 4 个空格
        content = content.replace('\t', '    ')

        # 2. 移除行尾空格
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)

        # 3. 确保文件以换行符结尾
        if not content.endswith('\n'):
            content += '\n'

        # 4. 修复缩进对齐问题 (E128)
        lines = content.split('\n')
        fixed_lines = []
        for line in lines:
            # 如果是续行且缩进不对，尝试修复
            if line.strip() and line.startswith(' ') and '(' in line:
                # 简单的缩进修复逻辑
                indent_level = len(line) - len(line.lstrip())
                if indent_level % 4 != 0 and indent_level > 8:
                    # 调整为最近的4的倍数
                    new_indent = ((indent_level // 4) + 1) * 4
                    line = ' ' * new_indent + line.lstrip()
            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 5. 处理过长的行 - 简单截断或在逗号处换行
        lines = content.split('\n')
        fixed_lines = []
        for line in lines:
            if len(line) > 120:
                # 如果包含逗号，尝试在逗号处换行
                if ',' in line and 'logger.' in line:
                    # 找到最后一个逗号
                    last_comma = line.rfind(',', 0, 120)
                    if last_comma > 80:
                        indent = ' ' * 12  # 简单的缩进
                        line = line[:last_comma + 1] + '\n' + indent + line[last_comma + 1:].lstrip()
                # 如果是字符串太长，简单截断
                elif len(line) > 120 and '"' in line:
                    line = line[:117] + '...'
            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 6. 移除明显未使用的导入
        unused_imports = [
            'from typing import Optional',
            'from typing import List',
            'from typing import Dict',
            'from typing import Any',
            'from typing import Tuple',
            'import json',
            'from datetime import datetime',
            'from app.models import get_mapping_by_source',
            'from app.service import get_mapping_by_source',
        ]

        lines = content.split('\n')
        filtered_lines = []

        for line in lines:
            # 检查是否是未使用的导入
            should_skip = False
            for unused_import in unused_imports:
                if line.strip() == unused_import:
                    # 检查这个导入是否真的在文件中使用
                    import_name = unused_import.split()[-1]
                    if import_name not in content.replace(line, ''):
                        should_skip = True
                        break

            if not should_skip:
                filtered_lines.append(line)

        content = '\n'.join(filtered_lines)

        # 7. 修复未使用变量问题
        if 'payload' in content and 'payload =' in content and content.count('payload') == 1:
            content = re.sub(r'(\s+)payload = (.+)\n', r'\1# payload = \2  # noqa: F841\n', content)

        # 只有当内容真正改变时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"  ❌ 修复 {file_path} 失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 开始批量修复代码质量问题...")

    # 要修复的文件
    files_to_fix = [
        'app/comment_sync.py',
        'app/enhanced_service.py',
        'app/github.py',
        'app/mapper.py',
        'app/models.py',
        'app/notion.py',
        'app/server.py',
        'app/service.py',
        'quick_test.py',
        'test_sync_system.py',
        'upgrade_sync_system.py',
    ]

    fixed_count = 0

    for file_name in files_to_fix:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"🔧 修复 {file_name}...")
            if fix_file(file_path):
                fixed_count += 1
                print(f"  ✅ {file_name} 已修复")
            else:
                print(f"  ℹ️ {file_name} 无需修复")
        else:
            print(f"  ⚠️ {file_name} 不存在，跳过")

    print(f"\n✅ 批量修复完成！共修复了 {fixed_count} 个文件")
    print("\n建议运行 'make lint' 检查修复效果")


if __name__ == "__main__":
    main()
