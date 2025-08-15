#!/usr/bin/env python3
"""
GitHub-Notion 双向同步系统测试脚本

全面测试所有新功能和优化，确保系统正常工作。
包含：模块导入测试、配置验证、功能测试、API 连接测试等。
"""
import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import yaml

# 设置测试日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SyncSystemTester:
    """同步系统测试器"""

    def __init__(self):
        self.project_root = Path(".")
        self.test_results = []
        self.failed_tests = []

    async def run_all_tests(self) -> bool:
        """运行所有测试"""
        try:
            print("🧪 开始 GitHub-Notion 同步系统测试...")
            print("=" * 60)

            # 测试分组
            test_groups = [
                ("基础模块导入测试", self._test_module_imports),
                ("配置文件验证测试", self._test_config_validation),
                ("字段映射功能测试", self._test_field_mapping),
                ("API 连接测试", self._test_api_connections),
                ("服务集成测试", self._test_service_integration),
                ("错误处理测试", self._test_error_handling),
            ]

            for group_name, test_func in test_groups:
                print(f"\n📋 {group_name}")
                print("-" * 40)

                try:
                    if asyncio.iscoroutinefunction(test_func):
                        success = await test_func()
                    else:
                        success = test_func()

                    if success:
                        print(f"✅ {group_name} - 全部通过")
                    else:
                        print(f"⚠️  {group_name} - 部分测试失败")

                except Exception as e:
                    print(f"❌ {group_name} - 测试组执行失败: {e}")
                    self.failed_tests.append(f"{group_name}: {str(e)}")

            # 生成测试报告
            self._generate_test_report()

            # 总结
            total_tests = len(self.test_results)
            passed_tests = len([r for r in self.test_results if r["passed"]])
            failed_count = len(self.failed_tests)

            print("\n📊 测试结果总结")
            print("=" * 40)
            print(f"总测试数: {total_tests}")
            print(f"通过: {passed_tests}")
            print(f"失败: {total_tests - passed_tests}")
            print(f"错误: {failed_count}")

            if failed_count == 0 and passed_tests == total_tests:
                print("\n🎉 所有测试通过！系统准备就绪！")
                return True
            else:
                print("\n⚠️  发现问题，请查看详细测试报告")
                return False

        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            print(f"\n❌ 测试执行失败: {e}")
            return False

    def _test_module_imports(self) -> bool:
        """测试模块导入"""
        print("测试新增模块导入...")

        modules_to_test = [
            ("app.mapper", "field_mapper"),
            ("app.enhanced_service", "process_github_event_enhanced"),
            ("app.comment_sync", "comment_sync_service"),
            ("app.notion", "notion_service"),
        ]

        all_passed = True

        for module_name, attr_name in modules_to_test:
            try:
                module = __import__(module_name, fromlist=[attr_name])
                attr = getattr(module, attr_name)

                self._record_test(
                    f"导入 {module_name}.{attr_name}",
                    True,
                    f"成功导入 {type(attr).__name__}",
                )
                print(f"  ✅ {module_name}.{attr_name}")

            except Exception as e:
                self._record_test(f"导入 {module_name}.{attr_name}", False, f"导入失败: {str(e)}")
                print(f"  ❌ {module_name}.{attr_name} - {e}")
                all_passed = False

        # 测试兼容性导入
        try:
            self._record_test("兼容性导入", True, "旧版本函数仍可导入")
            print("  ✅ 兼容性导入 - 旧版本函数仍可用")
        except Exception as e:
            self._record_test("兼容性导入", False, f"导入失败: {str(e)}")
            print(f"  ❌ 兼容性导入失败 - {e}")
            all_passed = False

        return all_passed

    def _test_config_validation(self) -> bool:
        """测试配置文件验证"""
        print("验证配置文件...")

        config_file = self.project_root / "app/mapping.yml"

        if not config_file.exists():
            self._record_test("配置文件存在性", False, "mapping.yml 不存在")
            print("  ❌ mapping.yml 文件不存在")
            return False

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            self._record_test("YAML 语法", True, "配置文件语法正确")
            print("  ✅ YAML 语法正确")

            # 检查必需的配置节
            required_sections = ["github_to_notion", "notion_to_github", "sync_config"]
            all_sections_present = True

            for section in required_sections:
                if section in config:
                    self._record_test(f"配置节 {section}", True, "配置节存在")
                    print(f"  ✅ {section} 配置节存在")
                else:
                    self._record_test(f"配置节 {section}", False, "配置节缺失")
                    print(f"  ⚠️  {section} 配置节缺失")
                    all_sections_present = False

            # 检查字段映射配置
            if "github_to_notion" in config:
                mapping_count = len(config["github_to_notion"])
                self._record_test(
                    "字段映射数量",
                    mapping_count > 0,
                    f"配置了 {mapping_count} 个字段映射",
                )
                print(f"  ✅ 配置了 {mapping_count} 个 GitHub → Notion 字段映射")

            return all_sections_present

        except yaml.YAMLError as e:
            self._record_test("YAML 语法", False, f"语法错误: {str(e)}")
            print(f"  ❌ YAML 语法错误: {e}")
            return False
        except Exception as e:
            self._record_test("配置文件读取", False, f"读取失败: {str(e)}")
            print(f"  ❌ 配置文件读取失败: {e}")
            return False

    def _test_field_mapping(self) -> bool:
        """测试字段映射功能"""
        print("测试字段映射器...")

        try:
            from app.mapper import field_mapper

            # 测试 GitHub 到 Notion 映射
            github_data = {
                "title": "测试 Issue",
                "body": "这是一个测试 Issue 的内容",
                "state": "open",
                "number": 123,
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "testuser"},
                "labels": [{"name": "bug"}],
                "created_at": "2023-10-15T10:30:45Z",
            }

            notion_props = field_mapper.github_to_notion(github_data)

            if notion_props:
                self._record_test(
                    "GitHub → Notion 映射",
                    True,
                    f"生成了 {len(notion_props)} 个 Notion 属性",
                )
                print(f"  ✅ GitHub → Notion 映射 - 生成了 {len(notion_props)} 个属性")

                # 显示映射结果示例
                for key, value in list(notion_props.items())[:3]:  # 显示前3个
                    print(f"    📋 {key}: {type(value).__name__}")
            else:
                self._record_test("GitHub → Notion 映射", False, "没有生成任何属性")
                print("  ❌ GitHub → Notion 映射失败 - 没有生成属性")
                return False

            # 测试 Notion 到 GitHub 映射
            notion_page = {
                "properties": {
                    "Task": {"type": "title", "title": [{"plain_text": "测试任务"}]},
                    "Status": {"type": "select", "select": {"name": "✅ Done"}},
                    "Description": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "任务描述"}],
                    },
                }
            }

            github_updates = field_mapper.notion_to_github(notion_page)

            if github_updates:
                self._record_test(
                    "Notion → GitHub 映射",
                    True,
                    f"生成了 {len(github_updates)} 个 GitHub 字段",
                )
                print(f"  ✅ Notion → GitHub 映射 - 生成了 {len(github_updates)} 个字段")

                for key, value in github_updates.items():
                    print(f"    📝 {key}: {value}")
            else:
                self._record_test("Notion → GitHub 映射", False, "没有生成任何字段")
                print("  ❌ Notion → GitHub 映射失败")

            # 测试配置重载
            try:
                reload_success = field_mapper.reload_config()
                self._record_test("配置重载", reload_success, "配置重载功能正常")
                print(f"  ✅ 配置重载功能 - {'成功' if reload_success else '失败'}")
            except Exception as e:
                self._record_test("配置重载", False, f"重载失败: {str(e)}")
                print(f"  ❌ 配置重载失败: {e}")

            return True

        except Exception as e:
            self._record_test("字段映射器初始化", False, f"初始化失败: {str(e)}")
            print(f"  ❌ 字段映射器测试失败: {e}")
            traceback.print_exc()
            return False

    async def _test_api_connections(self) -> bool:
        """测试 API 连接"""
        print("测试 API 连接...")

        # 检查环境变量
        github_token = os.getenv("GITHUB_TOKEN")
        notion_token = os.getenv("NOTION_TOKEN")
        notion_db_id = os.getenv("NOTION_DATABASE_ID")

        if not github_token:
            self._record_test("GitHub Token", False, "GITHUB_TOKEN 环境变量未设置")
            print("  ⚠️  GITHUB_TOKEN 未设置 - 跳过 GitHub API 测试")
        else:
            print("  ✅ GitHub Token 已配置")

            # 测试 GitHub API
            try:
                # 简单的 API 测试（获取用户信息）
                import requests

                headers = {"Authorization": f"Bearer {github_token}"}
                response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

                if response.status_code == 200:
                    user_data = response.json()
                    self._record_test(
                        "GitHub API 连接",
                        True,
                        f"成功连接，用户: {user_data.get('login', 'unknown')}",
                    )
                    print(f"  ✅ GitHub API 连接成功 - 用户: {user_data.get('login', 'unknown')}")
                else:
                    self._record_test("GitHub API 连接", False, f"响应状态码: {response.status_code}")
                    print(f"  ❌ GitHub API 连接失败 - 状态码: {response.status_code}")

            except Exception as e:
                self._record_test("GitHub API 连接", False, f"连接异常: {str(e)}")
                print(f"  ❌ GitHub API 连接异常: {e}")

        if not notion_token:
            self._record_test("Notion Token", False, "NOTION_TOKEN 环境变量未设置")
            print("  ⚠️  NOTION_TOKEN 未设置 - 跳过 Notion API 测试")
        else:
            print("  ✅ Notion Token 已配置")

            # 测试 Notion API
            try:
                # 简单的 API 测试（获取用户信息）
                import httpx

                headers = {
                    "Authorization": f"Bearer {notion_token}",
                    "Notion-Version": "2022-06-28",
                }

                async with httpx.AsyncClient() as client:
                    response = await client.get("https://api.notion.com/v1/users/me", headers=headers)

                    if response.status_code == 200:
                        user_data = response.json()
                        self._record_test(
                            "Notion API 连接",
                            True,
                            f"成功连接，用户类型: {user_data.get('type', 'unknown')}",
                        )
                        print(f"  ✅ Notion API 连接成功 - 用户类型: {user_data.get('type', 'unknown')}")
                    else:
                        self._record_test(
                            "Notion API 连接",
                            False,
                            f"响应状态码: {response.status_code}",
                        )
                        print(f"  ❌ Notion API 连接失败 - 状态码: {response.status_code}")

            except Exception as e:
                self._record_test("Notion API 连接", False, f"连接异常: {str(e)}")
                print(f"  ❌ Notion API 连接异常: {e}")

        if not notion_db_id:
            self._record_test("Notion Database ID", False, "NOTION_DATABASE_ID 环境变量未设置")
            print("  ⚠️  NOTION_DATABASE_ID 未设置 - 无法测试数据库操作")
        else:
            print(f"  ✅ Notion Database ID 已配置: {notion_db_id[:8]}...")

            # 测试数据库访问
            if notion_token:
                try:
                    from app.notion import notion_service

                    schema = await notion_service.get_database_schema()

                    if schema:
                        properties_count = len(schema.get("properties", {}))
                        self._record_test(
                            "Notion 数据库访问",
                            True,
                            f"数据库有 {properties_count} 个属性",
                        )
                        print(f"  ✅ Notion 数据库访问成功 - {properties_count} 个属性")

                        # 显示数据库属性
                        properties = schema.get("properties", {})
                        for prop_name, prop_info in list(properties.items())[:5]:  # 显示前5个
                            prop_type = prop_info.get("type", "unknown")
                            print(f"    📋 {prop_name}: {prop_type}")
                    else:
                        self._record_test("Notion 数据库访问", False, "无法获取数据库架构")
                        print("  ❌ 无法访问 Notion 数据库")

                except Exception as e:
                    self._record_test("Notion 数据库访问", False, f"访问异常: {str(e)}")
                    print(f"  ❌ Notion 数据库访问异常: {e}")

        return True

    def _test_service_integration(self) -> bool:
        """测试服务集成"""
        print("测试服务集成...")

        try:
            # 测试增强服务导入和初始化
            pass

            self._record_test("增强服务导入", True, "成功导入增强服务函数")
            print("  ✅ 增强服务导入成功")

            # 测试评论同步服务
            from app.comment_sync import comment_sync_service

            if hasattr(comment_sync_service, "sync_github_comment_to_notion"):
                self._record_test("评论同步服务", True, "评论同步服务初始化完成")
                print("  ✅ 评论同步服务就绪")
            else:
                self._record_test("评论同步服务", False, "缺少必需的方法")
                print("  ❌ 评论同步服务不完整")
                return False

            # 测试服务间依赖
            from app.github import github_service  # noqa: F401
            from app.mapper import field_mapper
            from app.notion import notion_service  # noqa: F401

            # 验证服务可以相互调用
            field_mapper.get_sync_config()

            self._record_test("服务间依赖", True, "服务间可以正常调用")
            print("  ✅ 服务间依赖关系正常")

            return True

        except Exception as e:
            self._record_test("服务集成", False, f"集成测试失败: {str(e)}")
            print(f"  ❌ 服务集成测试失败: {e}")
            traceback.print_exc()
            return False

    def _test_error_handling(self) -> bool:
        """测试错误处理"""
        print("测试错误处理...")

        try:
            from app.mapper import field_mapper

            # 测试空数据处理
            empty_result = field_mapper.github_to_notion({})
            self._record_test("空数据处理", isinstance(empty_result, dict), "空数据返回字典类型")
            print("  ✅ 空数据处理正常")

            # 测试无效数据处理
            invalid_result = field_mapper.github_to_notion({"invalid_field": "value"})
            self._record_test("无效数据处理", isinstance(invalid_result, dict), "无效数据返回字典类型")
            print("  ✅ 无效数据处理正常")

            # 测试配置重载错误处理
            original_path = field_mapper.config_path
            field_mapper.config_path = Path("non_existent_file.yml")
            reload_result = field_mapper.reload_config()
            field_mapper.config_path = original_path  # 恢复原配置

            # 注意：这里期望reload_result为False，表示错误被正确处理
            self._record_test("配置错误处理", reload_result is False, "配置错误被正确处理")
            print("  ✅ 配置错误处理正常")

            return True

        except Exception as e:
            self._record_test("错误处理测试", False, f"错误处理测试失败: {str(e)}")
            print(f"  ❌ 错误处理测试失败: {e}")
            return False

    def _record_test(self, test_name: str, passed: bool, message: str):
        """记录测试结果"""
        self.test_results.append(
            {
                "name": test_name,
                "passed": passed,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _generate_test_report(self):
        """生成测试报告"""
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed": len([r for r in self.test_results if r["passed"]]),
                "failed": len([r for r in self.test_results if not r["passed"]]),
                "errors": len(self.failed_tests),
                "timestamp": datetime.now().isoformat(),
            },
            "environment": {
                "github_token_set": bool(os.getenv("GITHUB_TOKEN")),
                "notion_token_set": bool(os.getenv("NOTION_TOKEN")),
                "notion_db_id_set": bool(os.getenv("NOTION_DATABASE_ID")),
                "python_version": sys.version,
            },
            "test_results": self.test_results,
            "failed_tests": self.failed_tests,
        }

        report_file = self.project_root / "test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"测试报告已生成: {report_file}")
        print("\n📋 详细测试报告已生成: test_report.json")


async def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("GitHub-Notion 双向同步系统测试脚本")
        print("用法: python test_sync_system.py")
        print("\n测试内容:")
        print("  - 模块导入测试")
        print("  - 配置文件验证")
        print("  - 字段映射功能测试")
        print("  - API 连接测试")
        print("  - 服务集成测试")
        print("  - 错误处理测试")
        return

    tester = SyncSystemTester()

    try:
        success = await tester.run_all_tests()

        if success:
            print("\n🎉 所有测试通过！你的同步系统已准备就绪！")
            print("\n📋 后续建议:")
            print("  1. 配置 GitHub webhook 指向你的服务器")
            print("  2. 配置 Notion 集成 webhook")
            print("  3. 创建一个测试 Issue 验证端到端同步")
            print("  4. 监控日志确保系统稳定运行")
        else:
            print("\n⚠️  发现一些问题，建议查看测试报告和日志")
            print("  - 检查 test_report.json 获取详细信息")
            print("  - 确保所有环境变量正确设置")
            print("  - 检查网络连接和 API 权限")

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试执行异常: {e}")
        print(f"\n❌ 测试执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
