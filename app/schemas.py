from __future__ import annotations

from typing import List, Optional, Union, Any, Dict

from pydantic import BaseModel


class User(BaseModel):
    name: Optional[str] = None
    login: Optional[str] = None  # GitHub username
    id: Optional[int] = None


class Label(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class Issue(BaseModel):
    id: Optional[Union[int, str]] = None
    number: Optional[Union[int, str]] = None
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    labels: Optional[List[Label]] = None
    user: Optional[User] = None
    html_url: Optional[str] = None  # GitHub issue URL
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GiteeWebhookPayload(BaseModel):
    action: Optional[str] = None
    issue: Issue


# GitHub Webhook Models
class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    html_url: str


class GitHubIssue(BaseModel):
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str  # open, closed
    labels: Optional[List[Label]] = None
    user: User
    html_url: str
    created_at: str
    updated_at: str


class GitHubWebhookPayload(BaseModel):
    action: str  # opened, edited, closed, reopened
    issue: GitHubIssue
    repository: GitHubRepository
    sender: User


# Notion Webhook Models
class NotionUser(BaseModel):
    object: str
    id: str
    type: Optional[str] = None
    name: Optional[str] = None


class NotionProperty(BaseModel):
    type: str
    # Dynamic properties based on type
    title: Optional[List[Dict[str, Any]]] = None
    rich_text: Optional[List[Dict[str, Any]]] = None
    select: Optional[Dict[str, Any]] = None
    multi_select: Optional[List[Dict[str, Any]]] = None
    number: Optional[float] = None
    checkbox: Optional[bool] = None
    date: Optional[Dict[str, Any]] = None
    url: Optional[str] = None


class NotionPage(BaseModel):
    object: str
    id: str
    created_time: str
    last_edited_time: str
    properties: Dict[str, NotionProperty]
    url: str


class NotionWebhookPayload(BaseModel):
    object: str
    id: str
    type: str  # page_updated, page_created, page_deleted
    page: Optional[NotionPage] = None
    user: NotionUser


# Sync Event Models for preventing loops
class SyncEvent(BaseModel):
    """同步事件模型，用于防循环"""
    event_id: str
    source: str  # 'github', 'notion'
    target: str  # 'github', 'notion'
    entity_type: str  # 'issue', 'page'
    entity_id: str
    action: str
    timestamp: str
    sync_hash: Optional[str] = None  # 防循环哈希
