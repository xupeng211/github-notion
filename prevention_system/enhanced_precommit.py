"""
增强的 Pre-commit Hook 系统
集成多种检查，确保代码质量
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class CheckResult:
    """检查结果"""

    name: str
    passed: bool
    message: str
    details: List[str]
    fix_command: str = ""


class EnhancedPreCommitSystem:
    """增强的Pre-commit系统"""

    def __init__(self):
        self.checks = []
        self._register_checks()

    def _register_checks(self):
        """注册所有检查"""
        self.checks = [
            self._check_example_values,
            self._check_test_completeness,
            self._check_database_compatibility,
            self._check_environment_consistency,
            self._check_documentation_sync,
        ]

    def _check_example_values(self) -> CheckResult:
        """检查示例值安全性"""
        from .example_value_manager import ExampleValueManager

        manager = ExampleValueManager()
        staged_files = self._get_staged_files()

        issues = []
        for filepath in staged_files:
            if os.path.exists(filepath):
                findings = manager.scan_file(filepath)
                high_risk = [f for f in findings if f.get("risk_level") == "high"]
                if high_risk:
                    issues.append(f"{filepath}: {len(high_risk)} high-risk example values")

        return CheckResult(
            name="Example Values Security",
            passed=len(issues) == 0,
            message=f"Found {len(issues)} files with dangerous example values"
            if issues
            else "No dangerous example values found",
            details=issues,
            fix_command="python -m prevention_system.example_value_manager fix --directory .",
        )

    def _check_test_completeness(self) -> CheckResult:
        """检查测试完整性"""
        staged_files = self._get_staged_files()

        # 检查是否有新的源文件但没有对应测试
        source_files = [f for f in staged_files if f.startswith("app/") and f.endswith(".py")]
        test_files = [f for f in staged_files if f.startswith("tests/") and f.endswith(".py")]

        missing_tests = []
        for source_file in source_files:
            # 跳过 __init__.py 和一些特殊文件
            if source_file.endswith("__init__.py") or "migration" in source_file:
                continue

            # 构造期望的测试文件名
            module_name = Path(source_file).stem
            expected_test = f"tests/test_{module_name}.py"

            if expected_test not in test_files and not os.path.exists(expected_test):
                missing_tests.append(f"{source_file} -> {expected_test}")

        return CheckResult(
            name="Test Completeness",
            passed=len(missing_tests) == 0,
            message=f"Missing tests for {len(missing_tests)} source files"
            if missing_tests
            else "All source files have corresponding tests",
            details=missing_tests,
            fix_command="Create missing test files",
        )

    def _check_database_compatibility(self) -> CheckResult:
        """检查数据库兼容性"""
        staged_files = self._get_staged_files()

        # 检查模型文件变更
        model_files = [f for f in staged_files if "models.py" in f or "model" in f]

        issues = []
        for model_file in model_files:
            if os.path.exists(model_file):
                # 检查是否使用了自适应查询模式
                with open(model_file, "r") as f:
                    content = f.read()

                # 检查是否有直接的字段访问而没有兼容性检查
                if "source_platform" in content and "adaptive" not in content.lower():
                    issues.append(f"{model_file}: Direct source_platform access without compatibility check")

                # 检查是否有新的数据库字段
                if "Column(" in content and "nullable=False" in content:
                    issues.append(f"{model_file}: New non-nullable column may break existing databases")

        return CheckResult(
            name="Database Compatibility",
            passed=len(issues) == 0,
            message=f"Found {len(issues)} potential database compatibility issues"
            if issues
            else "No database compatibility issues",
            details=issues,
            fix_command="Use adaptive query patterns or add migration scripts",
        )

    def _check_environment_consistency(self) -> CheckResult:
        """检查环境一致性"""
        staged_files = self._get_staged_files()

        # 检查环境配置文件
        env_files = [f for f in staged_files if ".env" in f or "docker-compose" in f or "requirements" in f]

        issues = []
        for env_file in env_files:
            if os.path.exists(env_file):
                # 检查是否有硬编码的环境特定值
                with open(env_file, "r") as f:
                    content = f.read()

                if "localhost" in content and "example" not in env_file:
                    issues.append(f"{env_file}: Contains localhost references")

                if any(port in content for port in ["3306", "5432", "6379"]) and "example" not in env_file:
                    issues.append(f"{env_file}: Contains hardcoded port numbers")

        return CheckResult(
            name="Environment Consistency",
            passed=len(issues) == 0,
            message=f"Found {len(issues)} environment consistency issues"
            if issues
            else "Environment configuration is consistent",
            details=issues,
            fix_command="Use environment variables instead of hardcoded values",
        )

    def _check_documentation_sync(self) -> CheckResult:
        """检查文档同步"""
        staged_files = self._get_staged_files()

        # 检查是否有API变更但文档未更新
        api_files = [f for f in staged_files if f.startswith("app/") and ("server.py" in f or "api" in f)]
        doc_files = [f for f in staged_files if f.endswith(".md") or "doc" in f.lower()]

        issues = []
        if api_files and not doc_files:
            issues.append("API files changed but no documentation updated")

        # 检查README是否需要更新
        if any("requirements" in f for f in staged_files):
            if "README.md" not in staged_files:
                issues.append("Dependencies changed but README.md not updated")

        return CheckResult(
            name="Documentation Sync",
            passed=len(issues) == 0,
            message=f"Found {len(issues)} documentation sync issues" if issues else "Documentation is in sync",
            details=issues,
            fix_command="Update relevant documentation files",
        )

    def _get_staged_files(self) -> List[str]:
        """获取暂存的文件"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            return []

    def run_all_checks(self) -> Tuple[bool, List[CheckResult]]:
        """运行所有检查"""
        results = []
        all_passed = True

        for check_func in self.checks:
            try:
                result = check_func()
                results.append(result)
                if not result.passed:
                    all_passed = False
            except Exception as e:
                results.append(
                    CheckResult(
                        name=check_func.__name__,
                        passed=False,
                        message=f"Check failed with error: {e}",
                        details=[str(e)],
                    )
                )
                all_passed = False

        return all_passed, results

    def generate_report(self, results: List[CheckResult]) -> str:
        """生成检查报告"""
        lines = []
        lines.append("🔍 Pre-commit Check Report")
        lines.append("=" * 50)

        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        lines.append(f"Overall Status: {passed_count}/{total_count} checks passed")
        lines.append("")

        for result in results:
            status = "✅" if result.passed else "❌"
            lines.append(f"{status} {result.name}")
            lines.append(f"   {result.message}")

            if result.details:
                for detail in result.details:
                    lines.append(f"   - {detail}")

            if not result.passed and result.fix_command:
                lines.append(f"   Fix: {result.fix_command}")

            lines.append("")

        return "\n".join(lines)

    def run_interactive_fix(self, results: List[CheckResult]):
        """交互式修复"""
        failed_results = [r for r in results if not r.passed]

        if not failed_results:
            print("✅ All checks passed!")
            return

        print(f"❌ {len(failed_results)} checks failed. Would you like to fix them?")

        for result in failed_results:
            if not result.fix_command:
                continue

            print(f"\n🔧 Fix for {result.name}:")
            print(f"   Command: {result.fix_command}")

            response = input("   Run this fix? (y/n/s=skip): ").lower()

            if response == "y":
                try:
                    subprocess.run(result.fix_command, shell=True, check=True)
                    print("   ✅ Fix applied successfully")
                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Fix failed: {e}")
            elif response == "s":
                continue
            else:
                print("   ⏭️  Skipped")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Pre-commit System")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive fix mode")
    parser.add_argument("--report", "-r", help="Save report to file")

    args = parser.parse_args()

    system = EnhancedPreCommitSystem()
    all_passed, results = system.run_all_checks()

    report = system.generate_report(results)

    if args.report:
        with open(args.report, "w") as f:
            f.write(report)
        print(f"Report saved to {args.report}")
    else:
        print(report)

    if args.interactive and not all_passed:
        system.run_interactive_fix(results)

    # 返回适当的退出码
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
