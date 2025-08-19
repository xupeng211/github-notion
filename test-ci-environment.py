#!/usr/bin/env python3
"""
测试CI环境配置
验证pytest和依赖是否正确安装
"""

import os
import subprocess
import sys


def test_python_environment():
    """测试Python环境"""
    print("🐍 Python环境检查:")
    print(f"   Python版本: {sys.version}")
    print(f"   Python路径: {sys.executable}")
    print(f"   当前工作目录: {os.getcwd()}")


def test_dependencies():
    """测试依赖安装"""
    print("\n📦 依赖检查:")

    required_packages = [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-asyncio",
        "responses",
        "fastapi",
        "sqlalchemy",
        "requests",
    ]

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - 未安装")


def test_app_imports():
    """测试应用模块导入"""
    print("\n🔧 应用模块检查:")

    app_modules = ["app.webhook_security", "app.service", "app.github", "app.notion", "app.models"]

    for module in app_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module} - {e}")


def test_pytest_config():
    """测试pytest配置"""
    print("\n🧪 Pytest配置检查:")

    # 检查pytest是否可以发现测试
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/priority/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            test_count = len([line for line in lines if "test_" in line])
            print(f"   ✅ 发现 {test_count} 个测试")
        else:
            print(f"   ❌ 测试发现失败:")
            print(f"      stdout: {result.stdout}")
            print(f"      stderr: {result.stderr}")

    except Exception as e:
        print(f"   ❌ pytest配置检查失败: {e}")


def test_environment_variables():
    """测试环境变量"""
    print("\n🌍 环境变量检查:")

    env_vars = ["ENVIRONMENT", "DISABLE_METRICS", "DISABLE_NOTION", "GITEE_WEBHOOK_SECRET", "GITHUB_WEBHOOK_SECRET"]

    for var in env_vars:
        value = os.environ.get(var, "NOT_SET")
        print(f"   {var}: {value}")


def run_simple_test():
    """运行一个简单的测试"""
    print("\n🚀 运行简单测试:")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/priority/security/", "-v", "--tb=short", "-x"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print("   ✅ 安全测试通过")
        else:
            print("   ❌ 安全测试失败:")
            print("   stdout:")
            print(result.stdout)
            print("   stderr:")
            print(result.stderr)

    except Exception as e:
        print(f"   ❌ 测试执行失败: {e}")


def main():
    print("🔍 CI环境诊断")
    print("=" * 50)

    test_python_environment()
    test_dependencies()
    test_app_imports()
    test_environment_variables()
    test_pytest_config()
    run_simple_test()

    print("\n✅ 诊断完成")


if __name__ == "__main__":
    main()
