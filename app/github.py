"""GitHub API 集成服务"""
import hashlib
import hmac
import json
import logging
import os
from typing import Dict, Any, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class GitHubService:
    """GitHub API 服务类"""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        self.base_url = "https://api.github.com"

        # 配置会话和重试策略
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证GitHub Webhook签名"""
        if not self.webhook_secret:
            logger.warning("GitHub webhook secret not configured")
            return False

        if not signature:
            return False

        # GitHub signature format: sha256=<hash>
        if not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # Remove "sha256=" prefix

        # Calculate HMAC
        calculated_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Use secure comparison
        return hmac.compare_digest(calculated_signature, expected_signature)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Optional[Dict[str, Any]]:
        """获取GitHub Issue"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get GitHub issue {owner}/{repo}#{issue_number}: {e}")
            return None

    def update_issue(self, owner: str, repo: str, issue_number: int,
                    title: Optional[str] = None, body: Optional[str] = None,
                    state: Optional[str] = None, labels: Optional[list] = None,
                    sync_marker: Optional[str] = None) -> Tuple[bool, str]:
        """更新GitHub Issue"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
            data = {}

            if title is not None:
                data["title"] = title
            if body is not None:
                # 添加同步标记到body中，用于防循环
                if sync_marker:
                    if f"<!-- sync-marker:{sync_marker} -->" not in (body or ""):
                        data["body"] = f"{body}\n\n<!-- sync-marker:{sync_marker} -->"
                    else:
                        data["body"] = body
                else:
                    data["body"] = body
            if state is not None:
                data["state"] = state
            if labels is not None:
                data["labels"] = labels

            response = self.session.patch(url, json=data, timeout=10)
            response.raise_for_status()

            logger.info(f"Successfully updated GitHub issue {owner}/{repo}#{issue_number}")
            return True, "success"

        except requests.RequestException as e:
            logger.error(f"Failed to update GitHub issue {owner}/{repo}#{issue_number}: {e}")
            return False, str(e)

    def add_comment(self, owner: str, repo: str, issue_number: int,
                   comment: str, sync_marker: Optional[str] = None) -> Tuple[bool, str]:
        """在GitHub Issue中添加评论"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"

            # 添加同步标记
            if sync_marker:
                comment = f"{comment}\n\n<!-- sync-marker:{sync_marker} -->"

            data = {"body": comment}
            response = self.session.post(url, json=data, timeout=10)
            response.raise_for_status()

            logger.info(f"Successfully added comment to GitHub issue {owner}/{repo}#{issue_number}")
            return True, "success"

        except requests.RequestException as e:
            logger.error(f"Failed to add comment to GitHub issue {owner}/{repo}#{issue_number}: {e}")
            return False, str(e)

    def has_sync_marker(self, content: str, marker: str) -> bool:
        """检查内容中是否包含同步标记"""
        return f"<!-- sync-marker:{marker} -->" in (content or "")

    def generate_sync_hash(self, data: Dict[str, Any]) -> str:
        """生成同步哈希，用于防循环"""
        # 使用关键字段生成哈希
        key_fields = {
            "title": data.get("title", ""),
            "body": data.get("body", ""),
            "state": data.get("state", ""),
            "updated_at": data.get("updated_at", "")
        }
        content = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def extract_repo_info(self, github_url: str) -> Optional[Tuple[str, str]]:
        """从GitHub URL中提取owner和repo信息"""
        try:
            # 处理形如 https://github.com/owner/repo 的URL
            if "github.com" in github_url:
                parts = github_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    return parts[-2], parts[-1]  # owner, repo
        except Exception as e:
            logger.error(f"Failed to extract repo info from URL {github_url}: {e}")
        return None


# 全局实例
github_service = GitHubService()
