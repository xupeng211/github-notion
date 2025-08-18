#!/usr/bin/env python3
"""
GitHub Workflows Secrets 校验工具

用途：扫描 .github/workflows/*.yml 中的 secrets.* 引用，
     输出实际需要的 Secrets 列表，并与现有仓库 Secrets 做差异分析

作者：DevOps Assistant
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


# 颜色定义
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


@dataclass
class SecretInfo:
    name: str
    priority: str
    description: str
    files: List[str]
    lines: List[int]


class WorkflowValidator:
    def __init__(self):
        self.workflows_dir = Path(".github/workflows")
        self.expected_secrets = {
            "GITHUB_WEBHOOK_SECRET": ("必需", "GitHub webhook 签名验证密钥"),
            "NOTION_TOKEN": ("必需", "Notion API 访问令牌"),
            "NOTION_DATABASE_ID": ("必需", "Notion 目标数据库 ID"),
            "AWS_PRIVATE_KEY": ("必需", "EC2 SSH 私钥（PEM 格式）"),
            "GITHUB_TOKEN": ("推荐", "GitHub API 访问令牌"),
            "DEADLETTER_REPLAY_TOKEN": ("推荐", "死信队列管理令牌"),
        }
        self.deprecated_secrets = {
            "GITEE_WEBHOOK_SECRET": "Gitee 功能已移除",
            "GRAFANA_PASSWORD": "未在 workflows 中使用",
        }

    def print_header(self):
        print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
        print(f"{Colors.BLUE}🔍 GitHub Workflows Secrets 校验工具{Colors.NC}")
        print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
        print()

    def print_error(self, message: str):
        print(f"{Colors.RED}❌ 错误: {message}{Colors.NC}", file=sys.stderr)

    def print_success(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

    def print_warning(self, message: str):
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

    def print_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")

    def scan_workflow_files(self) -> Dict[str, SecretInfo]:
        """扫描 workflow 文件中的 secrets 引用"""
        secrets_found = {}

        if not self.workflows_dir.exists():
            self.print_error(f"Workflows 目录不存在: {self.workflows_dir}")
            return secrets_found

        # secrets.* 引用的正则表达式
        secret_pattern = re.compile(r"\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}")

        for workflow_file in self.workflows_dir.glob("*.yml"):
            try:
                with open(workflow_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    matches = secret_pattern.findall(line)
                    for secret_name in matches:
                        if secret_name not in secrets_found:
                            # 确定优先级
                            if secret_name in self.expected_secrets:
                                priority, description = self.expected_secrets[secret_name]
                            else:
                                priority, description = "未知", "在 workflow 中发现但未在期望清单中"

                            secrets_found[secret_name] = SecretInfo(
                                name=secret_name, priority=priority, description=description, files=[], lines=[]
                            )

                        secrets_found[secret_name].files.append(str(workflow_file))
                        secrets_found[secret_name].lines.append(line_num)

            except Exception as e:
                self.print_warning(f"读取文件失败 {workflow_file}: {e}")

        return secrets_found

    def get_current_secrets(self) -> Set[str]:
        """获取当前仓库中已配置的 secrets"""
        try:
            # 获取仓库信息
            result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
            remote_url = result.stdout.strip()

            # 解析仓库名 - 支持多种 GitHub URL 格式
            repo_match = re.search(r"github\.com[:/]([^/]+)/([^/]+)(?:\.git)?$", remote_url)
            if not repo_match:
                # 如果不是 GitHub 仓库，尝试从环境变量获取
                github_repo = os.environ.get("GITHUB_REPO")
                if github_repo:
                    self.print_warning(f"当前仓库不是 GitHub: {remote_url}")
                    self.print_info(f"使用环境变量 GITHUB_REPO: {github_repo}")
                    owner, repo = github_repo.split("/")
                else:
                    self.print_error(f"无法解析 GitHub 仓库: {remote_url}")
                    self.print_info("提示: 设置环境变量 GITHUB_REPO=owner/repo 来指定 GitHub 仓库")
                    return set()
            else:
                owner, repo = repo_match.groups()

            repo = repo.rstrip(".git")
            repo_name = f"{owner}/{repo}"

            # 使用 gh CLI 获取 secrets 列表
            result = subprocess.run(
                ["gh", "secret", "list", "--repo", repo_name, "--json", "name"],
                capture_output=True,
                text=True,
                check=True,
            )

            secrets_data = json.loads(result.stdout)
            return {secret["name"] for secret in secrets_data}

        except subprocess.CalledProcessError as e:
            self.print_error(f"获取 secrets 失败: {e}")
            return set()
        except json.JSONDecodeError as e:
            self.print_error(f"解析 secrets 数据失败: {e}")
            return set()
        except Exception as e:
            self.print_error(f"未知错误: {e}")
            return set()

    def analyze_differences(self, workflow_secrets: Dict[str, SecretInfo], current_secrets: Set[str]) -> Dict:
        """分析差异"""
        workflow_secret_names = set(workflow_secrets.keys())
        set(self.expected_secrets.keys())
        deprecated_secret_names = set(self.deprecated_secrets.keys())

        # 分类分析
        missing_required = []
        missing_recommended = []
        missing_unknown = []
        extra_secrets = current_secrets - workflow_secret_names - deprecated_secret_names
        deprecated_found = current_secrets & deprecated_secret_names

        # 分析缺失的 secrets
        for secret_name in workflow_secret_names - current_secrets:
            secret_info = workflow_secrets[secret_name]
            if secret_info.priority == "必需":
                missing_required.append(secret_info)
            elif secret_info.priority == "推荐":
                missing_recommended.append(secret_info)
            else:
                missing_unknown.append(secret_info)

        return {
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
            "missing_unknown": missing_unknown,
            "extra_secrets": extra_secrets,
            "deprecated_found": deprecated_found,
            "workflow_secrets": workflow_secrets,
            "current_secrets": current_secrets,
        }

    def print_workflow_secrets(self, workflow_secrets: Dict[str, SecretInfo]):
        """打印 workflow 中发现的 secrets"""
        print(f"{Colors.CYAN}📋 Workflow 中发现的 Secrets:{Colors.NC}")
        print()

        if not workflow_secrets:
            print("  未发现任何 secrets 引用")
            return

        # 按优先级排序
        priority_order = {"必需": 1, "推荐": 2, "可选": 3, "未知": 4}
        sorted_secrets = sorted(workflow_secrets.values(), key=lambda x: (priority_order.get(x.priority, 5), x.name))

        for secret in sorted_secrets:
            priority_color = {
                "必需": Colors.RED,
                "推荐": Colors.YELLOW,
                "可选": Colors.GREEN,
                "未知": Colors.PURPLE,
            }.get(secret.priority, Colors.NC)

            print(f"  {priority_color}[{secret.priority}]{Colors.NC} {secret.name}")
            print(f"    描述: {secret.description}")

            # 显示文件位置（去重）
            unique_files = list(set(secret.files))
            for file_path in unique_files:
                file_lines = [str(line) for i, line in enumerate(secret.lines) if secret.files[i] == file_path]
                print(f"    位置: {file_path}:{','.join(file_lines)}")
            print()

    def print_analysis_results(self, analysis: Dict):
        """打印分析结果"""
        print(f"{Colors.CYAN}📊 差异分析结果:{Colors.NC}")
        print()

        # 缺失的必需 secrets
        if analysis["missing_required"]:
            print(f"{Colors.RED}❌ 缺失的必需 Secrets ({len(analysis['missing_required'])}):{Colors.NC}")
            for secret in analysis["missing_required"]:
                print(f"  - {secret.name}: {secret.description}")
            print()

        # 缺失的推荐 secrets
        if analysis["missing_recommended"]:
            print(f"{Colors.YELLOW}⚠️  缺失的推荐 Secrets ({len(analysis['missing_recommended'])}):{Colors.NC}")
            for secret in analysis["missing_recommended"]:
                print(f"  - {secret.name}: {secret.description}")
            print()

        # 缺失的未知 secrets
        if analysis["missing_unknown"]:
            print(f"{Colors.PURPLE}❓ 缺失的未知 Secrets ({len(analysis['missing_unknown'])}):{Colors.NC}")
            for secret in analysis["missing_unknown"]:
                print(f"  - {secret.name}: {secret.description}")
            print()

        # 多余的 secrets
        if analysis["extra_secrets"]:
            print(f"{Colors.BLUE}ℹ️  多余的 Secrets ({len(analysis['extra_secrets'])}):{Colors.NC}")
            for secret_name in sorted(analysis["extra_secrets"]):
                print(f"  - {secret_name}: 未在 workflows 中使用")
            print()

        # 废弃的 secrets
        if analysis["deprecated_found"]:
            print(f"{Colors.YELLOW}🗑️  废弃的 Secrets ({len(analysis['deprecated_found'])}):{Colors.NC}")
            for secret_name in sorted(analysis["deprecated_found"]):
                reason = self.deprecated_secrets.get(secret_name, "已废弃")
                print(f"  - {secret_name}: {reason}")
            print()

        # 总结
        total_missing = (
            len(analysis["missing_required"]) + len(analysis["missing_recommended"]) + len(analysis["missing_unknown"])
        )
        total_extra = len(analysis["extra_secrets"]) + len(analysis["deprecated_found"])

        print(f"{Colors.CYAN}📈 统计总结:{Colors.NC}")
        print(f"  Workflow 中的 Secrets: {len(analysis['workflow_secrets'])}")
        print(f"  当前已配置的 Secrets: {len(analysis['current_secrets'])}")
        print(f"  缺失的 Secrets: {total_missing}")
        print(f"  多余/废弃的 Secrets: {total_extra}")

        if total_missing == 0 and total_extra == 0:
            print()
            self.print_success("所有 Secrets 配置正确！")
        elif len(analysis["missing_required"]) == 0:
            print()
            self.print_warning("配置基本正确，但有一些建议优化")
        else:
            print()
            self.print_error("存在缺失的必需 Secrets，需要立即配置")

    def generate_config_commands(self, analysis: Dict):
        """生成配置命令"""
        missing_secrets = analysis["missing_required"] + analysis["missing_recommended"] + analysis["missing_unknown"]

        if not missing_secrets:
            return

        print(f"{Colors.CYAN}🛠️  建议的配置命令:{Colors.NC}")
        print()
        print("使用 configure_secrets.sh 工具:")
        print("  ./tools/configure_secrets.sh")
        print()
        print("或手动使用 gh CLI:")
        for secret in missing_secrets:
            print(
                f"  gh secret set {secret.name} --repo $(git remote get-url origin | sed -E 's#.*[:/](.+)/(.+)\\.git#\\1/\\2#')"
            )
        print()

    def run(self, verbose: bool = False):
        """运行校验"""
        self.print_header()

        # 扫描 workflow 文件
        self.print_info("扫描 workflow 文件...")
        workflow_secrets = self.scan_workflow_files()

        if verbose:
            self.print_workflow_secrets(workflow_secrets)

        # 获取当前 secrets
        self.print_info("获取当前仓库 secrets...")
        current_secrets = self.get_current_secrets()

        # 分析差异
        self.print_info("分析差异...")
        analysis = self.analyze_differences(workflow_secrets, current_secrets)

        # 打印结果
        self.print_analysis_results(analysis)
        self.generate_config_commands(analysis)

        # 返回状态码
        if analysis["missing_required"]:
            return 1  # 有必需的 secrets 缺失
        return 0


def main():
    parser = argparse.ArgumentParser(description="GitHub Workflows Secrets 校验工具")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")

    args = parser.parse_args()

    validator = WorkflowValidator()

    try:
        exit_code = validator.run(verbose=args.verbose)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作被用户取消{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.RED}未知错误: {e}{Colors.NC}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
