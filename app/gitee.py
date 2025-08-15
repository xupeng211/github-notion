import hashlib
import hmac
from typing import Any, Dict

import httpx


class GiteeClient:
    def __init__(self, token: str):
        self.token = token
        self.client = httpx.AsyncClient()
        self.headers = {"Authorization": f"token {self.token}", "Accept": "application/json"}

    async def update_issue(self, owner: str, repo: str, issue_id: int, data: Dict[str, Any]):
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/issues/{issue_id}"
        response = await self.client.patch(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    async def add_comment(self, owner: str, repo: str, issue_id: int, comment: str):
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/issues/{issue_id}/comments"
        response = await self.client.post(url, headers=self.headers, json={"body": comment})
        response.raise_for_status()
        return response.json()

    @staticmethod
    def verify_signature(token: str, payload: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected_signature = hmac.new(token.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
