"""
示例值管理系统
统一管理所有示例值，避免硬编码安全问题
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Pattern, Tuple


@dataclass
class ExamplePattern:
    """示例模式定义"""

    name: str
    pattern: Pattern[str]
    replacement: str
    description: str
    risk_level: str  # 'high', 'medium', 'low'


class ExampleValueManager:
    """示例值管理器"""

    def __init__(self):
        self.patterns: List[ExamplePattern] = []
        self.safe_examples: Dict[str, str] = {}
        self._load_patterns()
        self._load_safe_examples()

    def _load_patterns(self):
        """加载危险模式"""
        self.patterns = [
            # GitHub Token 模式
            ExamplePattern(
                name="github_token",
                pattern=re.compile(r"ghp_[A-Za-z0-9]{36,}"),
                replacement="github_pat_example_not_real",
                description="GitHub Personal Access Token",
                risk_level="high",
            ),
            # GitHub App Token 模式
            ExamplePattern(
                name="github_app_token",
                pattern=re.compile(r"ghs_[A-Za-z0-9]{36,}"),
                replacement="github_app_example_not_real",
                description="GitHub App Token",
                risk_level="high",
            ),
            # Webhook Secret 模式
            ExamplePattern(
                name="webhook_secret",
                pattern=re.compile(r'["\']([^"\']*secret[^"\']*)["\']', re.IGNORECASE),
                replacement='"example-webhook-key"',
                description="Webhook Secret",
                risk_level="medium",
            ),
            # 数据库连接字符串模式
            ExamplePattern(
                name="database_url",
                pattern=re.compile(r"postgresql://[^:]+:[^@]+@[^/]+/\w+"),
                replacement="postgresql://username:password@hostname:5432/database",
                description="Database Connection String",
                risk_level="medium",
            ),
            # API Key 模式
            ExamplePattern(
                name="api_key",
                pattern=re.compile(r'["\']([A-Za-z0-9]{32,})["\']'),
                replacement='"example_api_key_not_real"',
                description="Generic API Key",
                risk_level="medium",
            ),
            # Notion Token 模式
            ExamplePattern(
                name="notion_token",
                pattern=re.compile(r"secret_[A-Za-z0-9]{43,}"),
                replacement="secret_example_notion_token_not_real",
                description="Notion Integration Token",
                risk_level="high",
            ),
            # JWT Token 模式
            ExamplePattern(
                name="jwt_token",
                pattern=re.compile(r"eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+"),
                replacement="eyJ_example_jwt_token_not_real",
                description="JWT Token",
                risk_level="high",
            ),
            # AWS Access Key 模式
            ExamplePattern(
                name="aws_access_key",
                pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
                replacement="AKIA_EXAMPLE_NOT_REAL",
                description="AWS Access Key",
                risk_level="high",
            ),
            # 密码模式
            ExamplePattern(
                name="password",
                pattern=re.compile(r'password["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE),
                replacement='password="example_password"',
                description="Password Field",
                risk_level="medium",
            ),
        ]

    def _load_safe_examples(self):
        """加载安全示例值"""
        self.safe_examples = {
            # 认证相关
            "github_token": "github_pat_example_replace_with_real",
            "github_app_token": "github_app_example_replace_with_real",
            "notion_token": "secret_example_notion_token_replace_with_real",
            "webhook_secret": "example-webhook-key",
            "api_key": "example_api_key_replace_with_real",
            "jwt_token": "eyJ_example_jwt_token_replace_with_real",
            "aws_access_key": "AKIA_EXAMPLE_REPLACE_WITH_REAL",
            "aws_secret_key": "example_aws_secret_key_replace_with_real",
            # 数据库相关
            "database_url": "postgresql://username:password@hostname:5432/database",
            "redis_url": "redis://username:password@hostname:6379/0",
            "mongodb_url": "mongodb://username:password@hostname:27017/database",
            # 服务配置
            "encryption_key": "example_encryption_key_32_chars_long",
            "signing_secret": "example_signing_secret_for_webhooks",
            "session_secret": "example_session_secret_for_cookies",
            # 第三方服务
            "slack_token": "xoxb-example-slack-token-not-real",
            "discord_token": "example_discord_token_not_real",
            "telegram_token": "123456789:example_telegram_token_not_real",
            # 通用占位符
            "placeholder_id": "example_id_replace_with_real",
            "placeholder_url": "https://example.com/replace-with-real-url",
            "placeholder_email": "example@example.com",
            "placeholder_domain": "example.com",
        }

    def scan_file(self, filepath: str) -> List[Dict]:
        """扫描文件中的危险示例值"""
        findings = []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception as e:
            return [{"error": f"Failed to read file: {e}"}]

        for pattern in self.patterns:
            matches = pattern.pattern.finditer(content)
            for match in matches:
                # 找到匹配的行号
                line_num = content[: match.start()].count("\n") + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                findings.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "line_content": line_content.strip(),
                        "pattern_name": pattern.name,
                        "matched_text": match.group(0),
                        "description": pattern.description,
                        "risk_level": pattern.risk_level,
                        "suggested_replacement": pattern.replacement,
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                    }
                )

        return findings

    def scan_directory(self, directory: str, extensions: List[str] = None) -> Dict[str, List[Dict]]:
        """扫描目录中的所有文件"""
        if extensions is None:
            extensions = [".py", ".yml", ".yaml", ".json", ".env", ".example", ".md", ".txt"]

        results = {}
        directory_path = Path(directory)

        for file_path in directory_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                # 跳过一些目录
                skip_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue

                findings = self.scan_file(str(file_path))
                if findings:
                    results[str(file_path)] = findings

        return results

    def fix_file(self, filepath: str, findings: List[Dict]) -> bool:
        """修复文件中的危险示例值"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return False

        # 按位置倒序排序，避免位置偏移
        findings_sorted = sorted(findings, key=lambda x: x["start_pos"], reverse=True)

        modified_content = content
        for finding in findings_sorted:
            start_pos = finding["start_pos"]
            end_pos = finding["end_pos"]
            replacement = finding["suggested_replacement"]

            modified_content = modified_content[:start_pos] + replacement + modified_content[end_pos:]

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(modified_content)
            return True
        except Exception:
            return False

    def generate_safe_example(self, example_type: str, context: str = "") -> str:
        """生成安全的示例值"""
        if example_type in self.safe_examples:
            return self.safe_examples[example_type]

        # 根据上下文生成
        if "token" in example_type.lower():
            return f"example_{example_type}_replace_with_real"
        elif "secret" in example_type.lower():
            return f"example-{example_type}-key"
        elif "password" in example_type.lower():
            return "example_password"
        elif "url" in example_type.lower():
            return "https://example.com/replace-with-real"
        else:
            return f"example_{example_type}_value"

    def create_example_config(self, template_path: str, output_path: str):
        """创建安全的示例配置文件"""
        findings = self.scan_file(template_path)

        if findings:
            self.fix_file(template_path, findings)

        # 复制到输出路径
        try:
            with open(template_path, "r") as src, open(output_path, "w") as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"Failed to create example config: {e}")

    def validate_examples(self, directory: str) -> Dict[str, Any]:
        """验证目录中的示例值是否安全"""
        scan_results = self.scan_directory(directory)

        summary = {
            "total_files_scanned": 0,
            "files_with_issues": len(scan_results),
            "total_issues": 0,
            "issues_by_risk": {"high": 0, "medium": 0, "low": 0},
            "issues_by_type": {},
            "files": scan_results,
        }

        for filepath, findings in scan_results.items():
            summary["total_issues"] += len(findings)

            for finding in findings:
                risk_level = finding["risk_level"]
                pattern_name = finding["pattern_name"]

                summary["issues_by_risk"][risk_level] += 1
                summary["issues_by_type"][pattern_name] = summary["issues_by_type"].get(pattern_name, 0) + 1

        return summary

    def generate_report(self, scan_results: Dict[str, Any], output_file: str = None) -> str:
        """生成扫描报告"""
        report_lines = []

        report_lines.append("# 示例值安全扫描报告")
        report_lines.append("")
        report_lines.append(f"扫描时间: {__import__('datetime').datetime.now().isoformat()}")
        report_lines.append(f"扫描文件数: {scan_results['total_files_scanned']}")
        report_lines.append(f"发现问题文件数: {scan_results['files_with_issues']}")
        report_lines.append(f"总问题数: {scan_results['total_issues']}")
        report_lines.append("")

        # 风险等级统计
        report_lines.append("## 风险等级分布")
        for risk, count in scan_results["issues_by_risk"].items():
            report_lines.append(f"- {risk.upper()}: {count}")
        report_lines.append("")

        # 问题类型统计
        report_lines.append("## 问题类型分布")
        for issue_type, count in scan_results["issues_by_type"].items():
            report_lines.append(f"- {issue_type}: {count}")
        report_lines.append("")

        # 详细问题列表
        report_lines.append("## 详细问题列表")
        for filepath, findings in scan_results["files"].items():
            report_lines.append(f"### {filepath}")
            for finding in findings:
                report_lines.append(
                    f"- 行 {finding['line']}: {finding['description']} ({finding['risk_level'].upper()})"
                )
                report_lines.append(f"  匹配内容: `{finding['matched_text']}`")
                report_lines.append(f"  建议替换: `{finding['suggested_replacement']}`")
            report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)

        return report_content


# CLI 工具
def main():
    """命令行工具主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="示例值安全管理工具")
    parser.add_argument("command", choices=["scan", "fix", "validate", "report"])
    parser.add_argument("--directory", "-d", default=".", help="扫描目录")
    parser.add_argument("--file", "-f", help="单个文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--auto-fix", action="store_true", help="自动修复问题")

    args = parser.parse_args()

    manager = ExampleValueManager()

    if args.command == "scan":
        if args.file:
            results = manager.scan_file(args.file)
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            results = manager.scan_directory(args.directory)
            print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.command == "validate":
        results = manager.validate_examples(args.directory)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif args.command == "report":
        results = manager.validate_examples(args.directory)
        report = manager.generate_report(results, args.output)
        if not args.output:
            print(report)

    elif args.command == "fix":
        if args.file:
            findings = manager.scan_file(args.file)
            if manager.fix_file(args.file, findings):
                print(f"Fixed {len(findings)} issues in {args.file}")
            else:
                print(f"Failed to fix {args.file}")
        else:
            results = manager.scan_directory(args.directory)
            fixed_count = 0
            for filepath, findings in results.items():
                if manager.fix_file(filepath, findings):
                    fixed_count += 1
                    print(f"Fixed {len(findings)} issues in {filepath}")
            print(f"Total files fixed: {fixed_count}")


if __name__ == "__main__":
    main()


# Pre-commit Hook 集成
class PreCommitHook:
    """Pre-commit Hook 集成"""

    def __init__(self):
        self.manager = ExampleValueManager()

    def check_staged_files(self) -> Tuple[bool, List[str]]:
        """检查暂存的文件"""
        import subprocess

        try:
            # 获取暂存的文件
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
            )
            staged_files = result.stdout.strip().split("\n")
            staged_files = [f for f in staged_files if f]  # 过滤空字符串
        except subprocess.CalledProcessError:
            return False, ["Failed to get staged files"]

        issues = []
        has_issues = False

        for filepath in staged_files:
            if not os.path.exists(filepath):
                continue

            findings = self.manager.scan_file(filepath)
            if findings:
                has_issues = True
                high_risk_findings = [f for f in findings if f.get("risk_level") == "high"]
                if high_risk_findings:
                    issues.append(f"HIGH RISK: {filepath} contains {len(high_risk_findings)} high-risk example values")
                else:
                    issues.append(f"WARNING: {filepath} contains {len(findings)} example value issues")

        return not has_issues, issues

    def run_pre_commit_check(self) -> int:
        """运行pre-commit检查"""
        success, issues = self.check_staged_files()

        if not success:
            print("❌ Pre-commit check failed: Dangerous example values detected")
            print("\nIssues found:")
            for issue in issues:
                print(f"  - {issue}")
            print("\nPlease fix these issues before committing.")
            print("Run: python -m prevention_system.example_value_manager fix --directory .")
            return 1
        else:
            print("✅ Pre-commit check passed: No dangerous example values found")
            return 0
