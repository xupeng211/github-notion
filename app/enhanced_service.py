"""
增强的同步服务模块

集成新的字段映射器、评论同步和改进的双向同步逻辑，
提供更完整和强大的 GitHub ↔ Notion 同步功能。
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Tuple

from app.comment_sync import comment_sync_service
from app.github import github_service
from app.mapper import field_mapper
from app.notion import notion_service
from app.service import (
    DEADLETTER_SIZE,
    EVENTS_TOTAL,
    NOTION_DATABASE_ID,
    PROCESS_LATENCY,
    _get_issue_lock,
    create_sync_event,
    deadletter_count,
    deadletter_enqueue,
    event_hash_from_bytes,
    get_mapping_by_notion_page,
    mark_event_processed,
    mark_sync_event_processed,
    session_scope,
    should_skip_event,
    should_skip_sync_event,
    upsert_mapping,
)

logger = logging.getLogger(__name__)


async def process_github_event_enhanced(body_bytes: bytes, event: str) -> Tuple[bool, str]:
    """增强的 GitHub 事件处理

    Args:
        body_bytes: 请求体字节
        event: 事件类型

    Returns:
        Tuple[成功标志, 消息]
    """
    start = time.time()
    try:
        payload = json.loads(body_bytes.decode("utf-8"))

        # 支持多种事件类型
        if event == "issues":
            return await _handle_github_issue_event(payload, body_bytes)
        elif event == "issue_comment":
            return await _handle_github_comment_event(payload, body_bytes)
        else:
            EVENTS_TOTAL.labels("skip").inc()
            return True, f"ignored_event:{event}"

    except Exception as e:
        logger.error(f"Failed to process GitHub event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)
    finally:
        duration = time.time() - start
        PROCESS_LATENCY.observe(duration)


async def _handle_github_issue_event(payload: Dict[str, Any], body_bytes: bytes) -> Tuple[bool, str]:
    """处理 GitHub Issues 事件"""
    try:
        action = payload.get("action")
        issue = payload.get("issue") or {}
        repository = payload.get("repository") or {}

        # 提取基本信息
        owner = (repository.get("owner") or {}).get("login") or payload.get("organization", {}).get("login", "")
        repo = repository.get("name", "")
        issue_number = str(issue.get("number") or issue.get("id") or "")

        if not issue_number or not owner or not repo:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_required_fields"

        # 检查是否应该忽略此事件
        should_ignore, reason = field_mapper.should_ignore_event(payload, "github")
        if should_ignore:
            EVENTS_TOTAL.labels("skip").inc()
            return True, f"ignored:{reason}"

        # 防循环：检查同步标记
        if github_service.has_sync_marker(issue.get("body", ""), "notion-sync"):
            EVENTS_TOTAL.labels("skip").inc()
            return True, "sync_induced"

        # 幂等性处理
        event_hash = event_hash_from_bytes(body_bytes)

        lock = _get_issue_lock(f"github:{owner}/{repo}#{issue_number}")
        with lock:
            with session_scope() as db:
                if should_skip_event(db, issue_number, event_hash, platform="github"):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "duplicate"

                # 防循环：检查最近的同步事件
                if should_skip_sync_event(
                    db, event_hash, entity_id=issue_number, source_platform="github", target_platform="notion"
                ):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "loop_prevented"

                # 使用增强的 Notion 服务同步
                success, result = await notion_service.upsert_page_from_github(issue, field_mapper)

                if not success:
                    deadletter_enqueue(
                        db,
                        payload,
                        reason="notion_error",
                        last_error=result,
                        source_platform="github",
                        entity_id=issue_number,
                    )
                    DEADLETTER_SIZE.set(deadletter_count(db))
                    EVENTS_TOTAL.labels("fail").inc()
                    return False, "notion_error"

                # 更新映射关系
                if not result.startswith("ignored:"):
                    page_id = result
                    upsert_mapping(
                        db,
                        "github",
                        issue_number,
                        page_id,
                        source_url=issue.get("html_url"),
                        notion_database_id=NOTION_DATABASE_ID,
                    )

                    # 如果启用了评论同步，同步现有评论
                    sync_config = field_mapper.get_sync_config()
                    if sync_config.get("sync_comments", True) and action in ["opened", "reopened"]:
                        asyncio.create_task(_sync_issue_comments_to_notion(owner, repo, int(issue_number), page_id))

                mark_event_processed(db, issue_number, event_hash, platform="github")
                ev_id = create_sync_event(
                    db,
                    source_platform="github",
                    target_platform="notion",
                    entity_id=issue_number,
                    action=action or "updated",
                    event_hash=event_hash,
                    is_sync_induced=False,
                )
                mark_sync_event_processed(db, ev_id)

        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"

    except Exception as e:
        logger.error(f"Failed to handle GitHub issue event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)


async def _handle_github_comment_event(payload: Dict[str, Any], body_bytes: bytes) -> Tuple[bool, str]:
    """处理 GitHub 评论事件"""
    try:
        action = payload.get("action")
        comment = payload.get("comment") or {}
        issue = payload.get("issue") or {}

        # 只处理新创建的评论
        if action != "created":
            EVENTS_TOTAL.labels("skip").inc()
            return True, f"ignored_comment_action:{action}"

        # 检查同步配置
        sync_config = field_mapper.get_sync_config()
        if not sync_config.get("sync_comments", True):
            EVENTS_TOTAL.labels("skip").inc()
            return True, "comment_sync_disabled"

        # 防循环：检查同步标记
        comment_body = comment.get("body", "")
        if github_service.has_sync_marker(comment_body, "notion-sync"):
            EVENTS_TOTAL.labels("skip").inc()
            return True, "sync_induced_comment"

        # 同步评论到 Notion
        success, result = await comment_sync_service.sync_github_comment_to_notion(comment, issue)

        if success:
            EVENTS_TOTAL.labels("success").inc()
            return True, result
        else:
            EVENTS_TOTAL.labels("fail").inc()
            return False, result

    except Exception as e:
        logger.error(f"Failed to handle GitHub comment event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)


async def process_notion_event_enhanced(body_bytes: bytes) -> Tuple[bool, str]:
    """增强的 Notion 事件处理

    Args:
        body_bytes: 请求体字节

    Returns:
        Tuple[成功标志, 消息]
    """
    start = time.time()
    try:
        payload = json.loads(body_bytes.decode("utf-8"))

        # 解析事件类型
        event_type = payload.get("type", "")

        if event_type == "page_updated":
            return await _handle_notion_page_event(payload, body_bytes)
        elif event_type == "block_created":
            return await _handle_notion_block_event(payload, body_bytes)
        else:
            EVENTS_TOTAL.labels("skip").inc()
            return True, f"ignored_notion_event:{event_type}"

    except Exception as e:
        logger.error(f"Failed to process Notion event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)
    finally:
        duration = time.time() - start
        PROCESS_LATENCY.observe(duration)


async def _handle_notion_page_event(payload: Dict[str, Any], body_bytes: bytes) -> Tuple[bool, str]:
    """处理 Notion 页面更新事件"""
    try:
        page = payload.get("page") or {}
        page_id = page.get("id") or payload.get("id")

        if not page_id:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_page_id"

        # 防循环：检查同步标记
        sync_marker = notion_service.generate_sync_marker(page)

        event_hash = event_hash_from_bytes(body_bytes)

        with session_scope() as db:
            mapping = get_mapping_by_notion_page(db, page_id)
            if not mapping:
                EVENTS_TOTAL.labels("skip").inc()
                return True, "unmapped_page"

            issue_number = mapping.source_id
            platform = mapping.source_platform

            if platform != "github":
                EVENTS_TOTAL.labels("skip").inc()
                return True, "non_github_mapping"

            # 防重复处理
            if should_skip_event(db, issue_number, event_hash, platform="notion"):
                EVENTS_TOTAL.labels("skip").inc()
                return True, "duplicate"

            # 防循环
            if should_skip_sync_event(
                db, event_hash, entity_id=issue_number, source_platform="notion", target_platform="github"
            ):
                EVENTS_TOTAL.labels("skip").inc()
                return True, "loop_prevented"

            # 获取完整的页面数据
            full_page = await notion_service.get_page(page_id)
            if not full_page:
                EVENTS_TOTAL.labels("fail").inc()
                return False, "failed_to_get_page"

            # 使用字段映射器转换数据
            github_updates = field_mapper.notion_to_github(full_page)
            if not github_updates:
                EVENTS_TOTAL.labels("skip").inc()
                return True, "no_updates_mapped"

            # 提取仓库信息
            repo_info = github_service.extract_repo_info(mapping.source_url or "")
            if not repo_info:
                EVENTS_TOTAL.labels("fail").inc()
                return False, "missing_repo_info"

            owner, repo = repo_info

            # 更新 GitHub Issue
            success, message = github_service.update_issue(
                owner,
                repo,
                int(issue_number),
                title=github_updates.get("title"),
                body=github_updates.get("body"),
                state=github_updates.get("state"),
                sync_marker=sync_marker,
            )

            if not success:
                deadletter_enqueue(
                    db,
                    payload,
                    reason="github_error",
                    last_error=message,
                    source_platform="notion",
                    entity_id=str(page_id),
                )
                DEADLETTER_SIZE.set(deadletter_count(db))
                EVENTS_TOTAL.labels("fail").inc()
                return False, "github_error"

            mark_event_processed(db, issue_number, event_hash, platform="notion")
            ev_id = create_sync_event(
                db,
                source_platform="notion",
                target_platform="github",
                entity_id=issue_number,
                action="updated",
                event_hash=event_hash,
                is_sync_induced=True,
            )
            mark_sync_event_processed(db, ev_id)

        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"

    except Exception as e:
        logger.error(f"Failed to handle Notion page event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)


async def _handle_notion_block_event(payload: Dict[str, Any], body_bytes: bytes) -> Tuple[bool, str]:
    """处理 Notion 块创建事件（评论同步）"""
    try:
        block = payload.get("block") or {}
        parent_id = block.get("parent", {}).get("page_id")

        if not parent_id:
            EVENTS_TOTAL.labels("skip").inc()
            return True, "no_parent_page"

        # 检查评论同步配置
        sync_config = field_mapper.get_sync_config()
        if not sync_config.get("sync_comments", True):
            EVENTS_TOTAL.labels("skip").inc()
            return True, "comment_sync_disabled"

        # 获取父页面数据
        page_data = await notion_service.get_page(parent_id)
        if not page_data:
            EVENTS_TOTAL.labels("skip").inc()
            return True, "failed_to_get_parent_page"

        # 同步评论到 GitHub
        success, result = await comment_sync_service.sync_notion_comment_to_github(block, page_data)

        if success:
            EVENTS_TOTAL.labels("success").inc()
            return True, result
        else:
            EVENTS_TOTAL.labels("fail").inc()
            return False, result

    except Exception as e:
        logger.error(f"Failed to handle Notion block event: {e}")
        EVENTS_TOTAL.labels("fail").inc()
        return False, str(e)


async def _sync_issue_comments_to_notion(owner: str, repo: str, issue_number: int, notion_page_id: str) -> None:
    """异步同步 Issue 的所有评论到 Notion（后台任务）"""
    try:
        await comment_sync_service.sync_all_comments_github_to_notion(owner, repo, issue_number, notion_page_id)
        logger.info(f"Successfully synced comments for issue #{issue_number} to Notion")
    except Exception as e:
        logger.error(f"Failed to sync comments for issue #{issue_number}: {e}")


async def sync_existing_issues_to_notion(owner: str, repo: str, limit: int = 50) -> Tuple[bool, str]:
    """批量同步现有的 GitHub Issues 到 Notion

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        limit: 同步数量限制

    Returns:
        Tuple[成功标志, 同步结果]
    """
    try:
        # 获取仓库的 Issues
        url = f"{github_service.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": "all", "per_page": min(limit, 100), "sort": "updated", "direction": "desc"}

        response = github_service.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        issues = response.json()

        if not issues:
            return True, "no_issues_found"

        synced_count = 0
        failed_count = 0

        for issue in issues:
            try:
                # 跳过 Pull Requests（在 GitHub API 中也是 issues）
                if issue.get("pull_request"):
                    continue

                success, result = await notion_service.upsert_page_from_github(issue, field_mapper)

                if success and not result.startswith("ignored:"):
                    synced_count += 1

                    # 可选：同步评论
                    sync_config = field_mapper.get_sync_config()
                    if sync_config.get("sync_comments", True):
                        issue_number = issue.get("number")
                        if issue_number:
                            asyncio.create_task(_sync_issue_comments_to_notion(owner, repo, issue_number, result))
                elif not success:
                    failed_count += 1
                    logger.warning(f"Failed to sync issue #{issue.get('number')}: {result}")

                # 添加延迟以避免触发 API 限制
                sync_config = field_mapper.get_sync_config()
                delay = sync_config.get("rate_limit_delay", 1.0)
                if delay > 0:
                    await asyncio.sleep(delay)

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to process issue #{issue.get('number')}: {e}")

        result_msg = f"synced:{synced_count},failed:{failed_count}"
        logger.info(f"Bulk sync completed: {result_msg}")
        return True, result_msg

    except Exception as e:
        logger.error(f"Failed to sync existing issues: {e}")
        return False, str(e)


# 兼容性函数：包装原有的同步函数
def process_github_event_sync(body_bytes: bytes, event: str) -> Tuple[bool, str]:
    """同步版本的 GitHub 事件处理（兼容性）"""
    try:
        return asyncio.get_event_loop().run_until_complete(process_github_event_enhanced(body_bytes, event))
    except RuntimeError:
        # 如果没有事件循环，创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process_github_event_enhanced(body_bytes, event))
        finally:
            loop.close()


def process_notion_event_sync(body_bytes: bytes) -> Tuple[bool, str]:
    """同步版本的 Notion 事件处理（兼容性）"""
    try:
        return asyncio.get_event_loop().run_until_complete(process_notion_event_enhanced(body_bytes))
    except RuntimeError:
        # 如果没有事件循环，创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process_notion_event_enhanced(body_bytes))
        finally:
            loop.close()
