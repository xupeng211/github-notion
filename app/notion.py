"""
增强的 Notion API 集成服务

提供与 Notion API 的全面集成功能，包括页面管理、数据库操作、
webhook 验证和双向同步支持。
"""
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import httpx
import yaml

logger = logging.getLogger(__name__)


class NotionService:
    """增强的 Notion API 服务类"""
    
    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        """初始化 Notion 服务
        
        Args:
            token: Notion API 令牌，如果不提供则从环境变量获取
            database_id: 数据库 ID，如果不提供则从环境变量获取
        """
        self.token = token or os.getenv("NOTION_TOKEN", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self.webhook_secret = os.getenv("NOTION_WEBHOOK_SECRET", "")
        self.base_url = "https://api.notion.com/v1"
        
        # 配置 HTTP 客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
        )
        
        logger.info("Notion service initialized")
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证 Notion webhook 签名
        
        Args:
            payload: 请求体字节
            signature: 签名头
            
        Returns:
            签名验证结果
        """
        if not self.webhook_secret:
            logger.warning("Notion webhook secret not configured")
            return False
            
        if not signature:
            return False
        
        try:
            # Notion 使用 HMAC-SHA256
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # 移除可能的前缀
            if signature.startswith("sha256="):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Failed to verify Notion webhook signature: {e}")
            return False
    
    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """获取 Notion 页面
        
        Args:
            page_id: 页面 ID
            
        Returns:
            页面数据或 None
        """
        try:
            url = f"{self.base_url}/pages/{page_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get Notion page {page_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Notion page {page_id}: {e}")
            return None
    
    async def query_database(self, database_id: Optional[str] = None, 
                           filter_conditions: Optional[Dict[str, Any]] = None,
                           sorts: Optional[List[Dict[str, Any]]] = None,
                           page_size: int = 100) -> Optional[Dict[str, Any]]:
        """查询 Notion 数据库
        
        Args:
            database_id: 数据库 ID，默认使用配置的数据库
            filter_conditions: 过滤条件
            sorts: 排序条件
            page_size: 分页大小
            
        Returns:
            查询结果或 None
        """
        try:
            db_id = database_id or self.database_id
            if not db_id:
                logger.error("No database ID provided")
                return None
            
            url = f"{self.base_url}/databases/{db_id}/query"
            payload = {"page_size": page_size}
            
            if filter_conditions:
                payload["filter"] = filter_conditions
            if sorts:
                payload["sorts"] = sorts
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to query Notion database: {e}")
            return None
    
    async def create_page(self, properties: Dict[str, Any], 
                         database_id: Optional[str] = None) -> Tuple[bool, str]:
        """创建 Notion 页面
        
        Args:
            properties: 页面属性
            database_id: 数据库 ID，默认使用配置的数据库
            
        Returns:
            Tuple[成功标志, 页面ID或错误信息]
        """
        try:
            db_id = database_id or self.database_id
            if not db_id:
                return False, "No database ID configured"
            
            url = f"{self.base_url}/pages"
            payload = {
                "parent": {"database_id": db_id},
                "properties": properties
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            page_id = result.get("id")
            logger.info(f"Successfully created Notion page: {page_id}")
            return True, page_id
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to create Notion page: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            return False, str(e)
    
    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Tuple[bool, str]:
        """更新 Notion 页面
        
        Args:
            page_id: 页面 ID
            properties: 要更新的属性
            
        Returns:
            Tuple[成功标志, 成功信息或错误信息]
        """
        try:
            url = f"{self.base_url}/pages/{page_id}"
            payload = {"properties": properties}
            
            response = await self.client.patch(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully updated Notion page: {page_id}")
            return True, "success"
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to update Notion page {page_id}: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Failed to update Notion page {page_id}: {e}")
            return False, str(e)
    
    async def find_page_by_title(self, title: str, 
                                database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """根据标题查找页面
        
        Args:
            title: 页面标题
            database_id: 数据库 ID
            
        Returns:
            页面数据或 None
        """
        try:
            filter_conditions = {
                "property": "Task",  # 根据配置调整标题字段名
                "title": {"equals": title}
            }
            
            result = await self.query_database(
                database_id=database_id,
                filter_conditions=filter_conditions
            )
            
            if result and result.get("results"):
                return result["results"][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to find page by title '{title}': {e}")
            return None
    
    async def find_page_by_issue_id(self, issue_id: str,
                                   database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """根据 Issue ID 查找页面
        
        Args:
            issue_id: Issue ID
            database_id: 数据库 ID
            
        Returns:
            页面数据或 None
        """
        try:
            filter_conditions = {
                "property": "Issue ID",
                "rich_text": {"contains": str(issue_id)}
            }
            
            result = await self.query_database(
                database_id=database_id,
                filter_conditions=filter_conditions
            )
            
            if result and result.get("results"):
                return result["results"][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to find page by issue ID '{issue_id}': {e}")
            return None
    
    async def upsert_page_from_github(self, github_data: Dict[str, Any], 
                                     field_mapper) -> Tuple[bool, str]:
        """从 GitHub 数据创建或更新 Notion 页面
        
        Args:
            github_data: GitHub Issue 数据
            field_mapper: 字段映射器实例
            
        Returns:
            Tuple[成功标志, 页面ID或错误信息]
        """
        try:
            # 检查是否应该忽略此事件
            should_ignore, reason = field_mapper.should_ignore_event(github_data, 'github')
            if should_ignore:
                logger.info(f"Ignoring GitHub event: {reason}")
                return True, f"ignored:{reason}"
            
            # 使用字段映射器转换数据
            properties = field_mapper.github_to_notion(github_data)
            if not properties:
                logger.warning("No properties mapped from GitHub data")
                return False, "no_properties_mapped"
            
            issue_id = str(github_data.get("number", ""))
            if not issue_id:
                return False, "missing_issue_number"
            
            # 尝试查找现有页面
            existing_page = await self.find_page_by_issue_id(issue_id)
            
            if existing_page:
                # 更新现有页面
                page_id = existing_page["id"]
                success, message = await self.update_page(page_id, properties)
                return success, page_id if success else message
            else:
                # 创建新页面
                success, result = await self.create_page(properties)
                return success, result
                
        except Exception as e:
            logger.error(f"Failed to upsert page from GitHub data: {e}")
            return False, str(e)
    
    async def get_database_schema(self, database_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取数据库架构信息
        
        Args:
            database_id: 数据库 ID
            
        Returns:
            数据库架构信息或 None
        """
        try:
            db_id = database_id or self.database_id
            if not db_id:
                return None
            
            url = f"{self.base_url}/databases/{db_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}")
            return None
    
    def generate_sync_marker(self, data: Dict[str, Any]) -> str:
        """生成同步标记，用于防循环
        
        Args:
            data: 数据字典
            
        Returns:
            同步标记哈希
        """
        try:
            # 使用关键字段生成哈希
            key_fields = {
                "title": data.get("title", ""),
                "body": data.get("body", ""),
                "updated_time": data.get("last_edited_time", ""),
                "page_id": data.get("id", "")
            }
            content = json.dumps(key_fields, sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return hashlib.md5(str(data).encode()).hexdigest()
    
    async def add_comment_to_page(self, page_id: str, comment: str) -> Tuple[bool, str]:
        """向页面添加评论（通过块API）
        
        Args:
            page_id: 页面 ID
            comment: 评论内容
            
        Returns:
            Tuple[成功标志, 块ID或错误信息]
        """
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"
            
            # 创建段落块作为评论
            block_data = {
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": comment}
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = await self.client.patch(url, json=block_data)
            response.raise_for_status()
            result = response.json()
            
            block_id = result.get("results", [{}])[0].get("id", "")
            logger.info(f"Successfully added comment to Notion page {page_id}")
            return True, block_id
            
        except Exception as e:
            logger.error(f"Failed to add comment to page {page_id}: {e}")
            return False, str(e)


# 全局实例
notion_service = NotionService()


# 兼容性：保留旧的 NotionClient 类
class NotionClient(NotionService):
    """兼容性类，继承自 NotionService"""
    
    def __init__(self, token: str):
        super().__init__(token)
    
    def load_mapping(self, yml_path: str) -> Dict[str, str]:
        """加载映射配置（兼容旧接口）"""
        try:
            with open(yml_path, "r") as f:
                config = yaml.safe_load(f)
            return config.get("mapping", {})
        except Exception as e:
            logger.error(f"Failed to load mapping from {yml_path}: {e}")
            return {}
    
    async def sync_issue_to_notion(self, issue_data: Dict[str, Any], db):
        """同步 Issue 到 Notion（兼容旧接口）"""
        logger.warning("Using deprecated sync_issue_to_notion method")
        # 这里可以调用新的方法或保持向后兼容
        pass
