#!/usr/bin/env python3
"""
服务启动脚本

负责在启动主服务前完成必要的初始化操作，包括数据库迁移、
环境检查等。确保服务在健康的状态下启动。

使用方法:
    python scripts/start_service.py
    # 或者直接运行
    ./scripts/start_service.py

环境变量:
    PORT: 服务端口，默认 8000
    HOST: 服务主机，默认 0.0.0.0
    DB_URL: 数据库连接字符串
"""

import os
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def check_environment():
    """检查必要的环境变量"""
    print("检查环境配置...")

    required_vars = ["GITHUB_TOKEN", "NOTION_TOKEN", "NOTION_DATABASE_ID"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"✗ 缺少必要环境变量: {', '.join(missing_vars)}")
        print("请参考 env.example 配置环境变量")
        return False

    print("✓ 环境变量检查通过")
    return True


def init_database():
    """初始化数据库"""
    print("初始化数据库...")

    try:
        result = subprocess.run(
            [sys.executable, "scripts/init_db.py"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
        )

        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 数据库初始化失败:")
        print(e.stdout)
        print(e.stderr)
        return False


def start_uvicorn():
    """启动 FastAPI 服务"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"启动服务: http://{host}:{port}")

    # 使用 uvicorn 启动服务
    try:
        subprocess.run(
            [
                "uvicorn",
                "app.server:app",
                "--host",
                host,
                "--port",
                str(port),
                "--reload" if os.getenv("ENVIRONMENT") == "development" else "--no-reload",
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"✗ 服务启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n✓ 服务已停止")
        return True


def main():
    """主启动流程"""
    print("🚀 启动 GitHub-Notion 同步服务...")

    # 1. 检查环境变量
    if not check_environment():
        print("\n❌ 启动失败: 环境配置不完整")
        print("请运行 'python scripts/check_env.py' 检查详细配置")
        return False

    # 2. 初始化数据库
    if not init_database():
        print("\n❌ 启动失败: 数据库初始化失败")
        return False

    # 3. 启动服务
    print("\n✅ 预检完成，启动服务...")
    start_uvicorn()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
