from typing import Any, Dict

import httpx
import yaml


class NotionClient:
    def __init__(self, token: str):
        self.token = token
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def load_mapping(self, yml_path: str) -> Dict[str, str]:
        with open(yml_path, "r") as f:
            config = yaml.safe_load(f)
        return config.get("mapping", {})

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        response = await self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def update_page(self, page_id: str, properties: Dict[str, Any]):
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": properties}
        response = await self.client.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def create_page(self, parent_database_id: str, properties: Dict[str, Any]):
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": parent_database_id},
            "properties": properties
        }
        response = await self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def sync_issue_to_notion(self, issue_data: Dict[str, Any], db):
        mappings = self.load_mapping("app/mapping.yml")

        issue_id = issue_data.get("id")
        notion_page_id = db.get_mapping(issue_id)

        properties = {
            mappings["title"]: {"title": [{"text": {"content": issue_data["title"]}}]},
            mappings["state"]: {"select": {"name": issue_data["state"]}},
            mappings.get("labels.0.name"): {"select": {"name": issue_data.get("labels", [{}])[0].get("name", "")}},
            mappings["user.name"]: {"rich_text": [{"text": {"content": issue_data["user"]["name"]}}]},
            mappings["body"]: {"rich_text": [{"text": {"content": issue_data.get("body", "")}}]}
        }

        if notion_page_id:
            await self.update_page(notion_page_id, properties)
        else:
            parent_database_id = "YOUR_NOTION_DATABASE_ID"
            new_page = await self.create_page(parent_database_id, properties)
            db.insert_mapping(issue_id, new_page.get("id"))
