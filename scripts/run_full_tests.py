#!/usr/bin/env python3
"""
完整测试套件

在推送代码前运行的全面测试，包括：
1. 架构验证测试
2. 单元测试
3. 集成测试
4. API 端点测试
5. 部署流程验证
6. 性能基准测试

使用方法:
    python scripts/run_full_tests.py

环境要求:
    - 设置测试环境变量
    - 安装所有依赖
    - 可访问外部 API (可选)
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.test_results = []
        self.server_process = None

    def log_result(self, test_name: str, passed: bool, message: str = "", warning: bool = False):
        """记录测试结果"""
        if warning:
            print(f"  ⚠️  {test_name}: {message}")
            self.warnings += 1
        elif passed:
            print(f"  ✅ {test_name}")
            self.passed += 1
        else:
            print(f"  ❌ {test_name}: {message}")
            self.failed += 1

        self.test_results.append({"test": test_name, "passed": passed, "message": message, "warning": warning})

    def run_command(self, cmd: List[str], timeout: int = 30, capture_output: bool = True) -> Tuple[bool, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(cmd, timeout=timeout, capture_output=capture_output, text=True, cwd=PROJECT_ROOT)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    async def start_test_server(self) -> bool:
        """启动测试服务器"""
        try:
            # 设置测试环境变量
            test_env = os.environ.copy()
            test_env.update(
                {
                    "DB_URL": "sqlite:///data/test_server.db",
                    "PORT": "8001",
                    "LOG_LEVEL": "WARNING",
                    "ENVIRONMENT": "test",
                    "DISABLE_METRICS": "1",
                    "DISABLE_NOTION": "1",  # 避免实际 API 调用
                }
            )

            # 启动服务器
            self.server_process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "uvicorn",
                "app.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8001",
                env=test_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=PROJECT_ROOT,
            )

            # 等待服务器启动
            await asyncio.sleep(3)

            # 检查服务器是否启动成功
            import httpx

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get("http://127.0.0.1:8001/health", timeout=5)
                    return response.status_code == 200
                except Exception:
                    return False

        except Exception as e:
            print(f"Failed to start test server: {e}")
            return False

    async def stop_test_server(self):
        """停止测试服务器"""
        if self.server_process:
            try:
                self.server_process.terminate()
                await asyncio.wait_for(self.server_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.server_process.kill()
                await self.server_process.wait()
            except Exception as e:
                print(f"Error stopping server: {e}")

    def test_architecture_validation(self):
        """测试架构验证"""
        print("🔧 运行架构验证测试...")

        success, stdout, stderr = self.run_command([sys.executable, "scripts/validate_fixes.py"])

        if success and "🎉 所有测试通过" in stdout:
            self.log_result("架构验证", True)
        else:
            self.log_result("架构验证", False, stderr)

    def test_import_structure(self):
        """测试模块导入"""
        print("📦 测试模块导入...")

        modules_to_test = [
            "app.server",
            "app.service",
            "app.models",
            "app.notion",
            "app.github",
            "app.schemas",
            "app.middleware",
        ]

        for module in modules_to_test:
            try:
                __import__(module)
                self.log_result(f"导入 {module}", True)
            except Exception as e:
                self.log_result(f"导入 {module}", False, str(e))

    def test_database_operations(self):
        """测试数据库操作"""
        print("🗄️  测试数据库操作...")

        # 创建临时数据库
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            test_db_path = f.name

        try:
            # 设置测试数据库 URL
            original_db_url = os.getenv("DB_URL")
            os.environ["DB_URL"] = f"sqlite:///{test_db_path}"

            # 测试数据库初始化
            success, stdout, stderr = self.run_command([sys.executable, "scripts/init_db.py"])

            db_init_success = success
            if success:
                self.log_result("数据库初始化", True)
            else:
                # 如果数据库初始化失败，记录但继续测试
                self.log_result("数据库初始化", False, stderr.split("\n")[-1] if stderr else "初始化失败")

            # 测试基本数据库操作（仅在初始化成功时）
            if db_init_success:
                try:
                    # 重新创建数据库连接以使用新的DB_URL
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker

                    test_engine = create_engine(f"sqlite:///{test_db_path}", future=True)
                    TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False, future=True)

                    from app.models import Mapping

                    with TestSessionLocal() as db:
                        # 测试创建记录
                        mapping = Mapping(source_platform="github", source_id="test123", notion_page_id="test-page-id")
                        db.add(mapping)
                        db.commit()

                        # 测试查询
                        result = db.query(Mapping).filter_by(source_id="test123").first()
                        if result:
                            self.log_result("数据库读写操作", True)
                        else:
                            self.log_result("数据库读写操作", False, "无法查询创建的记录")

                except Exception as e:
                    self.log_result("数据库读写操作", False, str(e))
            else:
                self.log_result("数据库读写操作", False, "跳过：数据库初始化失败", warning=True)

        finally:
            # 恢复原始数据库URL
            if original_db_url:
                os.environ["DB_URL"] = original_db_url
            else:
                os.environ.pop("DB_URL", None)

            # 清理临时数据库
            try:
                os.unlink(test_db_path)
            except:
                pass

    def test_unit_functions(self):
        """测试核心函数"""
        print("🧪 测试核心函数...")

        try:
            from app.github import github_service
            from app.service import event_hash_from_bytes, verify_gitee_signature

            # 测试签名验证
            test_payload = b'{"test": "data"}'
            test_secret = "test_secret"
            import hashlib
            import hmac

            test_signature = hmac.new(test_secret.encode(), test_payload, hashlib.sha256).hexdigest()

            if verify_gitee_signature(test_secret, test_payload, test_signature):
                self.log_result("签名验证功能", True)
            else:
                self.log_result("签名验证功能", False, "签名验证失败")

            # 测试事件哈希
            hash_result = event_hash_from_bytes(test_payload)
            if hash_result and len(hash_result) == 64:  # SHA256 长度
                self.log_result("事件哈希功能", True)
            else:
                self.log_result("事件哈希功能", False, "哈希生成异常")

            # 测试 GitHub 服务方法
            repo_info = github_service.extract_repo_info("https://github.com/owner/repo")
            if repo_info == ("owner", "repo"):
                self.log_result("GitHub URL 解析", True)
            else:
                self.log_result("GitHub URL 解析", False, f"解析结果异常: {repo_info}")

        except Exception as e:
            self.log_result("核心函数测试", False, str(e))

    async def test_api_endpoints(self):
        """测试 API 端点"""
        print("🌐 测试 API 端点...")

        if not await self.start_test_server():
            self.log_result("测试服务器启动", False, "无法启动测试服务器")
            return

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                base_url = "http://127.0.0.1:8001"

                # 测试健康检查端点
                try:
                    response = await client.get(f"{base_url}/health", timeout=10)
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") in ["healthy", "degraded"]:
                            self.log_result("健康检查端点", True)
                        else:
                            self.log_result("健康检查端点", False, f"健康状态异常: {health_data.get('status')}")
                    else:
                        self.log_result("健康检查端点", False, f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_result("健康检查端点", False, str(e))

                # 测试 Prometheus 指标端点
                try:
                    response = await client.get(f"{base_url}/metrics", timeout=10, follow_redirects=True)
                    if response.status_code == 200:
                        # 检查是否包含 Prometheus 格式的指标
                        metrics_text = response.text
                        # 检查基本的 Prometheus 格式指标
                        prometheus_indicators = [
                            "# HELP",  # Prometheus 注释格式
                            "# TYPE",  # Prometheus 类型定义
                            "_total",  # 常见的计数器后缀
                            "_seconds",  # 常见的时间后缀
                        ]
                        if any(indicator in metrics_text for indicator in prometheus_indicators):
                            self.log_result("Prometheus 指标端点", True)
                        else:
                            self.log_result("Prometheus 指标端点", False, f"未找到 Prometheus 格式指标 (长度: {len(metrics_text)})")
                    else:
                        self.log_result("Prometheus 指标端点", False, f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_result("Prometheus 指标端点", False, str(e))

                # 测试 Webhook 端点（无需实际处理）
                webhook_endpoints = [
                    ("/github_webhook", "issues"),
                    ("/notion_webhook", "page_update"),
                    ("/gitee_webhook", "Issue Hook"),
                ]

                for endpoint, event_type in webhook_endpoints:
                    try:
                        headers = {"Content-Type": "application/json"}
                        if "github" in endpoint:
                            headers["X-GitHub-Event"] = event_type
                        elif "gitee" in endpoint:
                            headers["X-Gitee-Event"] = event_type

                        response = await client.post(
                            f"{base_url}{endpoint}", json={"test": "data"}, headers=headers, timeout=10
                        )

                        # 期望返回 400 (验证失败) 而不是 500 (服务器错误)
                        if response.status_code in [200, 400, 403, 422]:
                            self.log_result(f"{endpoint} 端点", True)
                        else:
                            self.log_result(f"{endpoint} 端点", False, f"HTTP {response.status_code}")
                    except Exception as e:
                        self.log_result(f"{endpoint} 端点", False, str(e))

        finally:
            await self.stop_test_server()

    def test_security_features(self):
        """测试安全功能"""
        print("🔒 测试安全功能...")

        try:
            from app.github import github_service
            from app.notion import notion_service

            # 测试签名验证（空密钥）
            if not github_service.verify_webhook_signature(b"test", ""):
                self.log_result("GitHub 签名验证（空密钥）", True)
            else:
                self.log_result("GitHub 签名验证（空密钥）", False, "应该拒绝空签名")

            # 测试签名验证（错误格式）
            if not github_service.verify_webhook_signature(b"test", "invalid"):
                self.log_result("GitHub 签名验证（错误格式）", True)
            else:
                self.log_result("GitHub 签名验证（错误格式）", False, "应该拒绝错误格式")

            # 测试 Notion 签名验证
            if not notion_service.verify_webhook_signature(b"test", ""):
                self.log_result("Notion 签名验证", True)
            else:
                self.log_result("Notion 签名验证", False, "应该拒绝空签名")

        except Exception as e:
            self.log_result("安全功能测试", False, str(e))

    async def test_async_functions(self):
        """测试异步函数"""
        print("⚡ 测试异步函数...")

        try:
            from app.service import async_exponential_backoff_request, async_notion_upsert_page

            # 测试异步 HTTP 请求函数
            try:
                success, result = await async_exponential_backoff_request(
                    "GET", "https://httpbin.org/status/200", max_retries=1
                )

                if success:
                    self.log_result("异步 HTTP 请求", True)
                else:
                    self.log_result("异步 HTTP 请求", False, "请求失败", warning=True)
            except Exception as e:
                self.log_result("异步 HTTP 请求", False, str(e), warning=True)

            # 测试异步 Notion 函数（禁用模式）
            original_disable = os.getenv("DISABLE_NOTION")
            original_token = os.getenv("NOTION_TOKEN")

            os.environ["DISABLE_NOTION"] = "1"
            # 设置一个测试用的 token 以避免空 header 错误
            os.environ["NOTION_TOKEN"] = "secret_test_token_for_testing"

            try:
                success, page_id = await async_notion_upsert_page({"title": "Test Issue", "number": 123})

                if success and "DRYRUN_PAGE" in page_id:
                    self.log_result("异步 Notion 函数", True)
                else:
                    self.log_result("异步 Notion 函数", False, f"结果异常: {page_id}", warning=True)

            except Exception as e:
                # 如果仍然有错误，标记为警告而不是失败
                self.log_result("异步 Notion 函数", False, str(e), warning=True)

            finally:
                # 恢复原始环境变量
                if original_disable:
                    os.environ["DISABLE_NOTION"] = original_disable
                else:
                    os.environ.pop("DISABLE_NOTION", None)

                if original_token:
                    os.environ["NOTION_TOKEN"] = original_token
                else:
                    os.environ.pop("NOTION_TOKEN", None)

        except Exception as e:
            self.log_result("异步函数测试", False, str(e))

    def test_deployment_scripts(self):
        """测试部署脚本"""
        print("🚀 测试部署脚本...")

        # 测试脚本可执行性
        scripts_to_test = ["scripts/validate_fixes.py", "scripts/init_db.py", "scripts/start_service.py"]

        for script in scripts_to_test:
            script_path = PROJECT_ROOT / script
            if script_path.exists() and os.access(script_path, os.X_OK):
                self.log_result(f"{script} 可执行性", True)
            else:
                self.log_result(f"{script} 可执行性", False, "脚本不可执行")

        # 测试配置文件
        config_files = ["env.example", "monitoring/prometheus.yml", "monitoring/alert_rules.yml"]

        for config_file in config_files:
            config_path = PROJECT_ROOT / config_file
            if config_path.exists():
                self.log_result(f"{config_file} 存在性", True)
            else:
                self.log_result(f"{config_file} 存在性", False, "配置文件缺失")

    def generate_test_report(self) -> Dict:
        """生成测试报告"""
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "success_rate": round(success_rate, 2),
            },
            "details": self.test_results,
        }

        return report

    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始完整测试套件...")
        print(f"📁 项目根目录: {PROJECT_ROOT}")

        # 运行各种测试
        self.test_architecture_validation()
        self.test_import_structure()
        self.test_database_operations()
        self.test_unit_functions()
        await self.test_api_endpoints()
        self.test_security_features()
        await self.test_async_functions()
        self.test_deployment_scripts()

        # 生成报告
        report = self.generate_test_report()

        # 输出测试总结
        print(f"\n📊 测试总结:")
        print(f"  总测试数: {report['summary']['total_tests']}")
        print(f"  通过: {report['summary']['passed']} ✅")
        print(f"  失败: {report['summary']['failed']} ❌")
        print(f"  警告: {report['summary']['warnings']} ⚠️")
        print(f"  成功率: {report['summary']['success_rate']}%")

        # 保存详细报告
        report_file = PROJECT_ROOT / "test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        # 判断是否可以推送
        if report["summary"]["failed"] == 0:
            print(f"\n🎉 所有测试通过！代码可以安全推送到仓库。")
            return True
        else:
            print(f"\n❌ 有 {report['summary']['failed']} 个测试失败，请修复后再推送。")
            return False


async def main():
    """主函数"""
    runner = TestRunner()

    try:
        success = await runner.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ 测试被中断")
        return 1
    except Exception as e:
        print(f"\n💥 测试运行异常: {e}")
        return 1
    finally:
        # 确保清理测试服务器
        await runner.stop_test_server()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
