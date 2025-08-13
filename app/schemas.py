from __future__ import annotations
from typing import Optional, List, Union
from pydantic import BaseModel

class User(BaseModel):
    name: Optional[str] = None

class Label(BaseModel):
    name: Optional[str] = None

class Issue(BaseModel):
    id: Optional[Union[int, str]] = None
    number: Optional[Union[int, str]] = None
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    labels: Optional[List[Label]] = None
    user: Optional[User] = None

class GiteeWebhookPayload(BaseModel):
    action: Optional[str] = None
    issue: Issue 