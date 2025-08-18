#!/usr/bin/env python3
"""
🔍 检测和修复硬编码值
"""
import os
import re
import sys


def fix_hardcoded_values():
    """修复常见的硬编码问题"""
    fixes_applied = 0

    # 定义需要检查的文件模式
    file_patterns = ["app/**/*.py", ".github/workflows/*.yml", ".github/workflows/*.yaml", "*.py"]

    # 硬编码模式和替换建议
    hardcode_patterns = {
        r"\b3\.35\.106\.116\b": "${AWS_SERVER}",
        r"\b8000\b(?=.*port)": "${APP_PORT}",
        r'"/opt/github-notion-sync"': '"${APP_DIR}"',
        r"'/opt/github-notion-sync'": "'${APP_DIR}'",
        r"\blocalhost:8000\b": "localhost:${APP_PORT}",
        r"\b:8000\b(?!.*\$)": ":${APP_PORT}",
    }

    print("🔍 检测硬编码值...")

    for root, dirs, files in os.walk("."):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in [".git", ".venv", "__pycache__", "node_modules"]]

        for file in files:
            if file.endswith((".py", ".yml", ".yaml")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    original_content = content

                    # 应用修复模式
                    for pattern, replacement in hardcode_patterns.items():
                        if re.search(pattern, content):
                            print(f"⚠️  发现硬编码: {file_path}")
                            print(f"   模式: {pattern}")
                            print(f"   建议: 使用环境变量 {replacement}")
                            # 注意：这里只是检测，不自动替换，避免破坏代码

                except Exception as e:
                    print(f"❌ 无法处理文件 {file_path}: {e}")

    print(f"✅ 硬编码检测完成")


if __name__ == "__main__":
    fix_hardcoded_values()
