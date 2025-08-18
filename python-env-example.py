#!/usr/bin/env python3
"""
🌐 Python 脚本中使用环境变量的示例
"""
import os

# ✅ 正确的方式：使用环境变量
AWS_SERVER = os.getenv("AWS_SERVER", "3.35.106.116")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_DIR = os.getenv("APP_DIR", "/opt/github-notion-sync")

# ❌ 错误的方式：硬编码
# AWS_SERVER = "3.35.106.116"
# APP_PORT = 8000
# APP_DIR = "/opt/github-notion-sync"


def main():
    print(f"服务器: {AWS_SERVER}")
    print(f"端口: {APP_PORT}")
    print(f"目录: {APP_DIR}")


if __name__ == "__main__":
    main()
