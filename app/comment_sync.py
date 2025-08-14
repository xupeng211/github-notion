"""
评论同步模块

实现 GitHub Issues 和 Notion 页面之间的评论双向同步功能。
支持评论的创建、更新和删除同步。
"""
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

from app.github import github_service
from app.notion import notion_service
from app.mapper import field_mapper

logger = logging.getLogger(__name__)


class CommentSyncService:
    """评论同步服务类"""

    def __init__(self):
        """初始化评论同步服务"""
        self.github_service = github_service
        self.notion_service = notion_service
        self.field_mapper = field_mapper

        logger.info("Comment sync service initialized")

    async def sync_github_comment_to_notion(self, comment_data: Dict[str, Any],
                                             issue_data: Dict[str, Any]) -> Tuple[bool, str]:
        """将 GitHub 评论同步到 Notion

        Args:
            comment_data: GitHub 评论数据
            issue_data: 关联的 GitHub Issue 数据

        Returns:
            Tuple[成功标志, 消息或错误信息]
        """
        try:
            # 检查同步配置
            sync_config = self.field_mapper.get_sync_config()
            if not sync_config.get('sync_comments', True):
                return True, "comment_sync_disabled"

            # 获取评论信息
            comment_body = comment_data.get('body', '')
            comment_author = comment_data.get('user', {}).get('login', 'Unknown')
            comment_created = comment_data.get('created_at', '')
            comment_url = comment_data.get('html_url', '')

            # 检查是否是同步标记（防循环）
            if self.github_service.has_sync_marker(comment_body, 'notion-sync'):
                logger.debug("Skipping sync marker comment from GitHub")
                return True, "sync_marker_detected"

            # 查找对应的 Notion 页面
            issue_number = str(issue_data.get('number', ''))
            if not issue_number:
                return False, "missing_issue_number"

            notion_page = await self.notion_service.find_page_by_issue_id(issue_number)
            if not notion_page:
                logger.warning(f"No Notion page found for GitHub issue #{issue_number}")
                return False, "notion_page_not_found"

            page_id = notion_page['id']

            # 构建评论内容，包含元数据
            formatted_comment = self._format_github_comment_for_notion(
                comment_body, comment_author, comment_created, comment_url
            )

            # 添加同步标记
            formatted_comment += f"\n\n<!-- notion-sync:{comment_data.get('id', '')} -->"

            # 添加评论到 Notion 页面
            success, result = await self.notion_service.add_comment_to_page(
                page_id, formatted_comment
            )

            if success:
                logger.info(f"Successfully synced GitHub comment to Notion page {page_id}")
                return True, result
            else:
                logger.error(f"Failed to sync GitHub comment to Notion: {result}")
                return False, result

        except Exception as e:
            logger.error(f"Failed to sync GitHub comment to Notion: {e}")
            return False, str(e)

    async def sync_notion_comment_to_github(self, notion_block: Dict[str, Any],
                                          page_data: Dict[str, Any]) -> Tuple[bool, str]:
        """将 Notion 评论同步到 GitHub

        Args:
            notion_block: Notion 块数据（评论）
            page_data: 关联的 Notion 页面数据

        Returns:
            Tuple[成功标志, 消息或错误信息]
        """
        try:
            # 检查同步配置
            sync_config = self.field_mapper.get_sync_config()
            if not sync_config.get('sync_comments', True):
                return True, "comment_sync_disabled"

            # 提取评论内容
            comment_text = self._extract_notion_block_text(notion_block)
            if not comment_text:
                return True, "empty_comment"

            # 检查是否是同步标记（防循环）
            if "<!-- github-sync:" in comment_text:
                logger.debug("Skipping sync marker comment from Notion")
                return True, "sync_marker_detected"

            # 从页面属性中获取 GitHub 仓库信息
            properties = page_data.get('properties', {})
            github_url_prop = properties.get('GitHub URL', {})
            github_url = github_url_prop.get('url', '') if github_url_prop else ''

            if not github_url:
                return False, "missing_github_url"

            # 提取仓库信息
            repo_info = self.github_service.extract_repo_info(github_url)
            if not repo_info:
                return False, "invalid_github_url"

            owner, repo = repo_info

            # 获取 Issue 编号
            issue_id_prop = properties.get('Issue ID', {})
            issue_number = None

            if issue_id_prop.get('rich_text'):
                try:
                    issue_text = issue_id_prop['rich_text'][0].get('plain_text', '')
                    issue_number = int(issue_text)
                except (ValueError, IndexError, TypeError):
                    return False, "invalid_issue_number"

            if not issue_number:
                return False, "missing_issue_number"

            # 构建评论内容，包含 Notion 来源信息
            formatted_comment = f"**来自 Notion 的评论：**\n\n{comment_text}"

            # 生成同步标记
            sync_marker = f"github-sync-{notion_block.get('id', '')[:8]}"

            # 添加评论到 GitHub
            success, message = self.github_service.add_comment(
                owner, repo, issue_number, formatted_comment, sync_marker
            )

            if success:
                logger.info(f"Successfully synced Notion comment to GitHub issue #{issue_number}")
                return True, "success"
            else:
                logger.error(f"Failed to sync Notion comment to GitHub: {message}")
                return False, message

        except Exception as e:
            logger.error(f"Failed to sync Notion comment to GitHub: {e}")
            return False, str(e)

    def _format_github_comment_for_notion(self, body: str, author: str,
                                         created_at: str, html_url: str) -> str:
        """格式化 GitHub 评论用于 Notion 显示

        Args:
            body: 评论内容
            author: 评论作者
            created_at: 创建时间
            html_url: GitHub 评论链接

        Returns:
            格式化后的评论内容
        """
        try:
            # 解析创建时间
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    formatted_date = created_at
            else:
                formatted_date = "Unknown"

            # 构建格式化评论
            formatted = f"""**GitHub 评论** by @{author} - {formatted_date}

{body}

[查看原评论]({html_url})"""

            return formatted

        except Exception as e:
            logger.error(f"Failed to format GitHub comment: {e}")
            return f"GitHub 评论 by {author}:\n\n{body}"

    def _extract_notion_block_text(self, block: Dict[str, Any]) -> str:
        """从 Notion 块中提取文本内容

        Args:
            block: Notion 块数据

        Returns:
            提取的文本内容
        """
        try:
            block_type = block.get('type', '')

            if block_type == 'paragraph':
                rich_text = block.get('paragraph', {}).get('rich_text', [])
            elif block_type == 'heading_1':
                rich_text = block.get('heading_1', {}).get('rich_text', [])
            elif block_type == 'heading_2':
                rich_text = block.get('heading_2', {}).get('rich_text', [])
            elif block_type == 'heading_3':
                rich_text = block.get('heading_3', {}).get('rich_text', [])
            elif block_type == 'bulleted_list_item':
                rich_text = block.get('bulleted_list_item', {}).get('rich_text', [])
            elif block_type == 'numbered_list_item':
                rich_text = block.get('numbered_list_item', {}).get('rich_text', [])
            else:
                return ""

            # 提取纯文本
            text_content = []
            for text_obj in rich_text:
                if text_obj.get('type') == 'text':
                    content = text_obj.get('text', {}).get('content', '')
                    text_content.append(content)
                elif text_obj.get('plain_text'):
                    text_content.append(text_obj['plain_text'])

            return ''.join(text_content).strip()

        except Exception as e:
            logger.error(f"Failed to extract text from Notion block: {e}")
            return ""

    async def get_github_comments(self, owner: str, repo: str,
                                issue_number: int) -> List[Dict[str, Any]]:
        """获取 GitHub Issue 的所有评论

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            issue_number: Issue 编号

        Returns:
            评论列表
        """
        try:
            url = f"{self.github_service.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
            response = await self.github_service.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitHub comments: {e}")
            return []

    async def get_notion_page_comments(self, page_id: str) -> List[Dict[str, Any]]:
        """获取 Notion 页面的所有评论（块）

        Args:
            page_id: 页面 ID

        Returns:
            块列表（包含评论）
        """
        try:
            url = f"{self.notion_service.base_url}/blocks/{page_id}/children"
            response = await self.notion_service.client.get(url)
            response.raise_for_status()
            result = response.json()

            # 过滤出可能包含评论的块
            comments = []
            for block in result.get('results', []):
                block_type = block.get('type', '')
                if block_type in ['paragraph', 'bulleted_list_item', 'numbered_list_item']:
                    text_content = self._extract_notion_block_text(block)
                    if text_content and not text_content.startswith('<!--'):  # 排除 HTML 注释
                        comments.append(block)

            return comments

        except Exception as e:
            logger.error(f"Failed to get Notion page comments: {e}")
            return []

    async def sync_all_comments_github_to_notion(self, owner: str, repo: str,
                                               issue_number: int,
                                               notion_page_id: str) -> Tuple[bool, str]:
        """同步 GitHub Issue 的所有评论到 Notion

        Args:
            owner: GitHub 仓库所有者
            repo: GitHub 仓库名称
            issue_number: Issue 编号
            notion_page_id: Notion 页面 ID

        Returns:
            Tuple[成功标志, 消息]
        """
        try:
            # 获取 GitHub 评论
            github_comments = await self.get_github_comments(owner, repo, issue_number)
            if not github_comments:
                return True, "no_comments_to_sync"

            # 获取 Issue 数据用于上下文
            issue_data = self.github_service.get_issue(owner, repo, issue_number)
            if not issue_data:
                return False, "failed_to_get_issue_data"

            success_count = 0
            for comment in github_comments:
                # 跳过已同步的评论（检查同步标记）
                comment_body = comment.get('body', '')
                if self.github_service.has_sync_marker(comment_body, 'notion-sync'):
                    continue

                success, message = await self.sync_github_comment_to_notion(comment, issue_data)
                if success:
                    success_count += 1
                else:
                    logger.warning(f"Failed to sync comment {comment.get('id')}: {message}")

            return True, f"synced_{success_count}_comments"

        except Exception as e:
            logger.error(f"Failed to sync all GitHub comments to Notion: {e}")
            return False, str(e)


# 全局实例
comment_sync_service = CommentSyncService()
