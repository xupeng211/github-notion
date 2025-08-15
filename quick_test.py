#!/usr/bin/env python3
"""
快速测试脚本 - GitHub-Notion 同步系统

快速验证基础功能是否正常，适合初次测试使用。
"""
import os
import sys
import traceback
from pathlib import Path


def print_status(message, status="info"):
    """打印带状态的消息"""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    print(f"{icons.get(status, 'ℹ️')} {message}")


def quick_test():
    """执行快速测试"""
    print("🚀 GitHub-Notion 同步系统快速测试")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    # 1. 测试文件存在性
    print("\n📁 检查关键文件...")
    key_files = ["app/mapper.py", "app/enhanced_service.py", "app/comment_sync.py", "app/mapping.yml"]

    for file_path in key_files:
        total_tests += 1
        if Path(file_path).exists():
            print_status(f"{file_path} 存在", "success")
            tests_passed += 1
        else:
            print_status(f"{file_path} 缺失", "error")

    # 2. 测试模块导入
    print("\n🔗 测试模块导入...")
    modules = [
        ("app.mapper", "field_mapper"),
        ("app.enhanced_service", "process_github_event_enhanced"),
        ("app.comment_sync", "comment_sync_service"),
    ]

    for module_name, attr_name in modules:
        total_tests += 1
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            print_status(f"{module_name} 导入成功", "success")
            tests_passed += 1
        except Exception as e:
            print_status(f"{module_name} 导入失败: {e}", "error")

    # 3. 测试配置文件
    print("\n⚙️ 测试配置文件...")
    total_tests += 1
    try:
        import yaml

        with open("app/mapping.yml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        required_sections = ["github_to_notion", "notion_to_github"]
        if all(section in config for section in required_sections):
            print_status("配置文件格式正确", "success")
            tests_passed += 1
        else:
            print_status("配置文件缺少必需节", "warning")
    except Exception as e:
        print_status(f"配置文件测试失败: {e}", "error")

    # 4. 测试字段映射
    print("\n🔄 测试字段映射...")
    total_tests += 1
    try:
        from app.mapper import field_mapper

        test_data = {"title": "测试", "state": "open"}
        result = field_mapper.github_to_notion(test_data)

        if isinstance(result, dict) and len(result) > 0:
            print_status(f"字段映射正常 (生成 {len(result)} 个属性)", "success")
            tests_passed += 1
        else:
            print_status("字段映射返回空结果", "warning")
    except Exception as e:
        print_status(f"字段映射测试失败: {e}", "error")

    # 5. 检查环境变量
    print("\n🔐 检查环境变量...")
    env_vars = ["GITHUB_TOKEN", "NOTION_TOKEN", "NOTION_DATABASE_ID"]

    for var in env_vars:
        if os.getenv(var):
            print_status(f"{var} 已设置", "success")
        else:
            print_status(f"{var} 未设置", "warning")

    # 总结
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {tests_passed}/{total_tests} 通过")

    if tests_passed == total_tests:
        print_status("快速测试全部通过！", "success")
        print("\n📋 建议下一步:")
        print("  1. 运行完整测试: python test_sync_system.py")
        print("  2. 配置环境变量（如果还未设置）")
        print("  3. 测试 API 连接")
        return True
    else:
        print_status(f"发现 {total_tests - tests_passed} 个问题", "warning")
        print("\n📋 建议:")
        print("  1. 检查缺失的文件")
        print("  2. 解决导入错误")
        print("  3. 运行完整测试获取详细信息")
        return False


if __name__ == "__main__":
    try:
        success = quick_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        traceback.print_exc()
        sys.exit(1)
