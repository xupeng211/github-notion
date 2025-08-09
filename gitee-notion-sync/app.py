#!/usr/bin/env python3

"""
Example Gitee ↔ Notion synchronization service (Flask).

* Listens for Gitee webhook events (Issue Hook).
* On issue open/update, creates or updates a page in the specified Notion database.
* On issue close, finds the corresponding page and updates its status.
* Relies on environment variables for secrets and tokens.
"""

import os
import json
import hmac
import hashlib
import requests
from flask import Flask, request, abort
import traceback
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
import time
from prometheus_client import Counter, Histogram, generate_latest
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# --- Load environment variables ---
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)

# --- Configuration validation ---
def validate_env_vars() -> Dict[str, str]:
    required_vars = {
        "NOTION_API_TOKEN": "Notion API token is required",
        "NOTION_DATABASE_ID": "Notion database ID is required",
    }
    config = {}
    for var, message in required_vars.items():
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Missing environment variable: {message}")
        config[var] = value
    config["ENVIRONMENT"] = os.getenv("ENVIRONMENT", "development")
    config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
    config["NOTION_API_VERSION"] = os.getenv("NOTION_API_VERSION", "2022-06-28")
    config["PORT"] = int(os.getenv("PORT", "8787"))
    config["HOST"] = os.getenv("HOST", "0.0.0.0")
    config["GITEE_WEBHOOK_SECRET"] = os.getenv("GITEE_WEBHOOK_SECRET", "")
    config["NOTION_WEBHOOK_SECRET"] = os.getenv("NOTION_WEBHOOK_SECRET", "")
    return config

# --- Initialize Configuration ---
try:
    config = validate_env_vars()
except ValueError as e:
    print(f"Configuration Error: {e}")
    exit(1)

def setup_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(config["LOG_LEVEL"])
    return logger

logger = setup_logger()

app = Flask(__name__)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

talisman = Talisman(
    app,
    force_https=False,
    strict_transport_security=True,
    session_cookie_secure=True,
    content_security_policy={
        'default-src': "'self'",
        'img-src': "'self' data: https:",
        'script-src': "'self'",
        'style-src': "'self' 'unsafe-inline'",
    }
)

@limiter.limit("5 per minute")
@app.route("/gitee_webhook", methods=["POST"])
def gitee_hook():
    logger.info("Received webhook request", extra={
        "headers": dict(request.headers),
        "endpoint": request.endpoint
    })
    if config["GITEE_WEBHOOK_SECRET"]:
        signature = request.headers.get("X-Gitee-Token")
        if not verify_gitee_signature(config["GITEE_WEBHOOK_SECRET"], request.data, signature):
            logger.warning("Invalid webhook signature")
            abort(403)
    event = request.headers.get("X-Gitee-Event")
    logger.info(f"Processing Gitee event", extra={"event_type": event})
    try:
        data = request.json
        if event == "Note Hook":
            issue_number = data.get("issue", {}).get("number")
            if issue_number:
                page_id = notion_find_page_by_title(data["issue"]["title"])
                if page_id:
                    sync_issue_comments(issue_number, page_id, data["comment"])
                    return "Comment synced", 200
                else:
                    logger.warning("No matching page found for comment", extra={"issue_number": issue_number})
                    return "No matching page found", 404
            return "Invalid payload", 400
        if event == "Issue Hook":
            action = data.get("action")
            issue = data.get("issue")
            if not action or not issue:
                logger.error("Invalid payload: missing action or issue")
                return "Invalid payload", 400
            if action in ["open", "update"]:
                notion_sync_issue(issue)
            elif action == "close":
                page_id = notion_find_page_by_title(issue["title"])
                if page_id:
                    notion_update_page_status(page_id, "closed")
                else:
                    logger.warning(f"No matching page found for issue", extra={"title": issue["title"]})
            elif action == "state_change":
                logger.info(f"Handling state change", extra={
                    "title": issue["title"],
                    "new_state": issue["state"]
                })
                page_id = notion_find_page_by_title(issue["title"])
                if page_id:
                    notion_update_page_status(page_id, issue["state"])
                else:
                    logger.warning(f"No matching page found for issue", extra={"title": issue["title"]})
            return "Webhook processed", 200
        logger.info(f"Ignoring non-issue event", extra={"event_type": event})
        return "Event ignored", 204
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP Error", extra={
            "status_code": e.response.status_code,
            "response_text": e.response.text,
            "traceback": traceback.format_exc()
        })
        abort(500)
    except Exception as e:
        logger.error("Unexpected error", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        abort(500)

@app.route("/notion_webhook", methods=["POST"])
def notion_webhook():
    """处理来自 Notion 的 webhook 请求，并将变化同步到 Gitee"""
    logger.info("Received Notion webhook request", extra={
        "headers": dict(request.headers),
        "endpoint": request.endpoint
    })
    if "Notion-Token" not in request.headers or request.headers["Notion-Token"] != config["NOTION_WEBHOOK_SECRET"]:
        logger.warning("Invalid Notion webhook token")
        return "Forbidden", 403
    try:
        data = request.json
        # 处理页面更新事件
        if data["type"] == "page_updated":
            page_id = data["page"]["id"]
            updated_properties = data.get("changes", {}).get("properties", {})
            gitee_issue_id = get_property_value(updated_properties, "Issue ID", "rich_text")
            if not gitee_issue_id:
                logger.warning("No Issue ID found for Notion page", extra={"page_id": page_id})
                return "Bad Request", 400
            
            update_data = {}
            
            # 处理状态更新
            if "Status" in updated_properties:
                status = get_property_value(updated_properties, "Status", "select", "name")
                if status:
                    update_data["state"] = status.lower()
            
            # 处理内容更新
            if "Content" in updated_properties:
                content = get_property_value(updated_properties, "Content", "rich_text")
                if content:
                    update_data["body"] = content

            # 处理标题更新
            if "Task" in updated_properties:
                title = get_property_value(updated_properties, "Task", "title")
                if title:
                    update_data["title"] = title
            
            # 处理标签/里程碑等其他可能的字段
            if "Tags" in updated_properties:
                tags = get_property_value(updated_properties, "Tags", "multi_select")
                if tags and isinstance(tags, list):
                    update_data["labels"] = ",".join([tag.get("name", "") for tag in tags if tag.get("name")])
            
            if update_data:
                # 从环境变量中获取仓库信息，而不是使用硬编码
                owner = os.getenv("GITEE_REPO_OWNER")
                repo = os.getenv("GITEE_REPO_NAME")
                if not owner or not repo:
                    logger.error("Missing repository information", extra={
                        "gitee_repo_owner": owner,
                        "gitee_repo_name": repo
                    })
                    return "Configuration error", 500
                update_gitee_issue(owner, repo, gitee_issue_id, update_data)
            return "Notion sync completed", 200
        
        # 处理页面创建事件
        elif data["type"] == "page_created":
            page_id = data["page"]["id"]
            # 获取页面详细信息
            page_data = get_notion_page(page_id)
            if not page_data:
                logger.error("Failed to get page data", extra={"page_id": page_id})
                return "Failed to process page", 500
            
            properties = page_data.get("properties", {})
            
            # 检查该页面是否已经有关联的Issue ID
            gitee_issue_id = get_page_property(properties, "Issue ID", "rich_text")
            if gitee_issue_id:
                logger.info("Page already has Issue ID, skipping creation", extra={"page_id": page_id, "issue_id": gitee_issue_id})
                return "Page already linked to issue", 200
            
            # 创建新Issue所需的数据
            issue_data = {}
            
            # 获取标题
            title = get_page_property(properties, "Task", "title")
            if not title:
                logger.warning("Missing title for new issue", extra={"page_id": page_id})
                return "Missing required fields", 400
            issue_data["title"] = title
            
            # 获取内容
            content = get_page_property(properties, "Content", "rich_text")
            if content:
                issue_data["body"] = content
            
            # 获取状态
            status = get_page_property(properties, "Status", "select", "name")
            if status:
                issue_data["state"] = status.lower()
            
            # 获取标签
            tags = get_page_property(properties, "Tags", "multi_select")
            if tags and isinstance(tags, list):
                issue_data["labels"] = ",".join([tag.get("name", "") for tag in tags if tag.get("name")])
            
            # 创建新Issue
            owner = os.getenv("GITEE_REPO_OWNER")
            repo = os.getenv("GITEE_REPO_NAME")
            if not owner or not repo:
                logger.error("Missing repository information", extra={
                    "gitee_repo_owner": owner,
                    "gitee_repo_name": repo
                })
                return "Configuration error", 500
            
            new_issue = create_gitee_issue(owner, repo, issue_data)
            if not new_issue:
                logger.error("Failed to create Gitee issue", extra={"page_id": page_id})
                return "Failed to create issue", 500
            
            # 更新Notion页面，添加Issue ID
            issue_number = new_issue.get("number")
            if issue_number:
                update_notion_page_issue_id(page_id, str(issue_number))
                logger.info("Created new Gitee issue and updated Notion", extra={
                    "page_id": page_id,
                    "issue_id": issue_number
                })
                return "New issue created", 201
            
            return "Failed to get issue number", 500
        
        # 其他事件类型
        else:
            logger.info(f"Unhandled event type", extra={"event_type": data.get("type")})
        return "Event type not handled", 204
    except Exception as e:
        logger.error("Error processing Notion webhook", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return "Internal error", 500

def verify_gitee_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not signature:
        logger.warning("No signature provided in Gitee webhook")
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def format_attachments(attachments: list) -> str:
    if not attachments:
        return ""
    formatted = "\n\n📎 附件:\n"
    for attachment in attachments:
        name = attachment.get("name", "未命名")
        url = attachment.get("url", "")
        formatted += f"- [{name}]({url})\n"
    return formatted

def sync_issue_attachments(page_id: str, attachments: list):
    logger.info("Syncing attachments", extra={
        "page_id": page_id,
        "attachment_count": len(attachments) if attachments else 0
    })
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        current_page = resp.json()
        current_output = ""
        if current_page["properties"]["Output"]["rich_text"]:
            current_output = current_page["properties"]["Output"]["rich_text"][0]["text"]["content"]
        attachments_text = format_attachments(attachments)
        properties = {
            "Attachments": {
                "rich_text": [{
                    "text": {
                        "content": attachments_text
                    }
                }]
            }
        }
        if attachments_text and attachments_text not in current_output:
            updated_output = current_output + attachments_text if current_output else attachments_text
            properties["Output"] = {
                "rich_text": [{
                    "text": {
                        "content": updated_output
                    }
                }]
            }
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": properties}
        resp = requests.patch(url, headers=headers, json=payload)
        resp.raise_for_status()
        logger.info("Successfully synced attachments", extra={
            "page_id": page_id,
            "attachment_count": len(attachments) if attachments else 0
        })
    except Exception as e:
        logger.error("Failed to sync attachments", extra={
            "error": str(e),
            "page_id": page_id,
            "traceback": traceback.format_exc()
        })
        raise

def notion_sync_issue(issue: dict):
    logger.info(f"Syncing issue", extra={"title": issue["title"]})
    properties = {
        "Task": {"title": [{"text": {"content": issue["title"]}}]},
        "Status": {"select": {"name": issue["state"]}},
        "Owner": {"rich_text": [{"text": {"content": issue["user"]["name"]}}]},
        "Output": {"rich_text": [{"text": {"content": issue.get("body", "")}}]},
        "Labels": {"multi_select": []},
    }
    if issue.get('labels'):
        for label in issue['labels']:
            properties["Labels"]["multi_select"].append({
                "name": label['name']
            })
    priority_content = None
    if issue.get('labels'):
        for label in issue['labels']:
            p_candidate = label['name'].lower()
            if p_candidate in ["high", "medium", "low"]:
                priority_content = p_candidate.capitalize()
                break
    if priority_content:
        properties["Priority"] = {"select": {"name": priority_content}}
    if issue.get('milestone') and issue['milestone'].get('title'):
        properties["Milestone"] = {"rich_text": [{"text": {"content": issue['milestone']['title']}}]}
    if issue.get('created_at'):
        start_date = issue['created_at'].split('T')[0]
        properties["Start"] = {"date": {"start": start_date}}
    if issue.get('due_date'):
        properties["End"] = {"date": {"start": issue['due_date']}}
    if issue.get('html_url'):
        properties["URL"] = {"url": issue['html_url']}
    if issue.get('number'):
        properties["Issue ID"] = {"rich_text": [{"text": {"content": issue['number']}}]}
    if 'comments' in issue:
        properties["Comments"] = {"number": issue['comments']}
    attachments = issue.get('attachments', [])
    if attachments:
        attachments_text = format_attachments(attachments)
        properties["Attachments"] = {
            "rich_text": [{
                "text": {
                    "content": attachments_text
                }
            }]
        }
        if issue.get("body"):
            properties["Output"]["rich_text"][0]["text"]["content"] += attachments_text
        else:
            properties["Output"]["rich_text"][0]["text"]["content"] = attachments_text
    page_id = notion_find_page_by_title(issue["title"])
    if page_id:
        logger.info(f"Updating existing page", extra={"page_id": page_id})
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": properties}
        resp = requests.patch(url, headers=headers, json=payload)
    else:
        logger.info(f"Creating new page", extra={"title": issue["title"]})
        payload = {
            "parent": {"database_id": config["NOTION_DATABASE_ID"]},
            "properties": properties
        }
        url = "https://api.notion.com/v1/pages"
        resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    logger.info(f"Successfully synced page", extra={"title": issue["title"]})

def notion_find_page_by_title(title: str):
    print(f"Searching for page with title: {title}")
    url = f"https://api.notion.com/v1/databases/{config['NOTION_DATABASE_ID']}/query"
    query = {"filter": {"property": "Task", "title": {"equals": title}}}
    resp = requests.post(url, headers=headers, json=query)
    print(f"Notion API Response (find_page): {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    results = resp.json().get("results")
    if results:
        page_id = results[0]["id"]
        print(f"Found page with ID: {page_id}")
        return page_id
    print("No matching page found.")
    return None

def notion_update_page_status(page_id: str, status: str):
    print(f"Updating page {page_id} to status: {status}")
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Status": {"select": {"name": status}}}}
    resp = requests.patch(url, headers=headers, json=payload)
    print(f"Notion API Response (update_status): {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    print(f"Successfully updated page {page_id}.")

def sync_issue_comments(issue_number: str, page_id: str, comment_data: dict):
    logger.info(f"Syncing comment", extra={
        "issue_number": issue_number,
        "page_id": page_id
    })
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        current_page = resp.json()
        current_output = ""
        if current_page["properties"]["Output"]["rich_text"]:
            current_output = current_page["properties"]["Output"]["rich_text"][0]["text"]["content"]
        comment_user = comment_data["user"]["name"]
        comment_body = comment_data["body"]
        comment_time = datetime.fromisoformat(comment_data["created_at"].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S")
        new_comment = f"\n\n---\n💬 {comment_user} 评论于 {comment_time}:\n{comment_body}"
        updated_content = current_output + new_comment if current_output else new_comment
        properties = {
            "Output": {
                "rich_text": [{
                    "text": {
                        "content": updated_content
                    }
                }]
            },
            "Comments": {
                "number": comment_data.get("comments", 0)
            }
        }
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": properties}
        resp = requests.patch(url, headers=headers, json=payload)
        resp.raise_for_status()
        logger.info("Successfully synced comment", extra={
            "issue_number": issue_number,
            "page_id": page_id
        })
    except Exception as e:
        logger.error("Failed to sync comment", extra={
            "error": str(e),
            "issue_number": issue_number,
            "page_id": page_id,
            "traceback": traceback.format_exc()
        })
        raise

headers = {
    "Authorization": f"Bearer {config['NOTION_API_TOKEN']}",
    "Notion-Version": config["NOTION_API_VERSION"],
    "Content-Type": "application/json",
}

GITEE_ACCESS_TOKEN = os.getenv("GITEE_ACCESS_TOKEN")

def update_gitee_issue(owner: str, repo: str, issue_number: str, data: dict):
    logger.info("Updating Gitee issue", extra={
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number
    })
    try:
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/issues/{issue_number}"
        headers2 = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"token {GITEE_ACCESS_TOKEN}"
        }
        resp = requests.patch(url, headers=headers2, json=data)
        resp.raise_for_status()
        logger.info("Successfully updated Gitee issue", extra={
            "issue_number": issue_number
        })
    except Exception as e:
        logger.error("Failed to update Gitee issue", extra={
            "error": str(e),
            "issue_number": issue_number,
            "traceback": traceback.format_exc()
        })
        raise

def add_gitee_comment(owner: str, repo: str, issue_number: str, comment: str):
    logger.info("Adding comment to Gitee issue", extra={
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number
    })
    try:
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers2 = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"token {GITEE_ACCESS_TOKEN}"
        }
        data = {"body": comment}
        resp = requests.post(url, headers=headers2, json=data)
        resp.raise_for_status()
        logger.info("Successfully added comment to Gitee issue", extra={
            "issue_number": issue_number
        })
    except Exception as e:
        logger.error("Failed to add comment to Gitee issue", extra={
            "error": str(e),
            "issue_number": issue_number,
            "traceback": traceback.format_exc()
        })
        raise

def verify_notion_signature(secret: str, payload: bytes, signature: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)
notion_api_requests_total = Counter(
    'notion_api_requests_total',
    'Total number of Notion API requests',
    ['operation', 'status']
)
gitee_webhook_requests_total = Counter(
    'gitee_webhook_requests_total',
    'Total number of Gitee webhook requests',
    ['event_type', 'status']
)
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain'}

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if request.path != '/metrics' and hasattr(request, 'start_time'):
        latency = time.time() - request.start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.path
        ).observe(latency)
    return response

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {e.description}")
    return {
        "error": "rate limit exceeded",
        "description": e.description
    }, 429

@app.errorhandler(403)
def forbidden_handler(e):
    logger.warning(f"Forbidden access: {str(e)}")
    return {
        "error": "forbidden",
        "description": str(e)
    }, 403

# 辅助函数，用于从Notion API响应中提取属性值
def get_property_value(properties, prop_name, prop_type, sub_field=None):
    """从更新的属性中提取特定类型的值"""
    try:
        if prop_name not in properties:
            return None
        
        if prop_type == "rich_text":
            return properties[prop_name].get("rich_text", [{}])[0].get("text", {}).get("content", "")
        elif prop_type == "title":
            return properties[prop_name].get("title", [{}])[0].get("text", {}).get("content", "")
        elif prop_type == "select" and sub_field:
            return properties[prop_name].get("select", {}).get(sub_field)
        elif prop_type == "multi_select":
            return properties[prop_name].get("multi_select", [])
        return None
    except (IndexError, KeyError, TypeError):
        return None

# 从完整页面属性中提取值
def get_page_property(properties, prop_name, prop_type, sub_field=None):
    """从页面属性中提取特定类型的值"""
    try:
        if prop_name not in properties:
            return None
        
        prop = properties[prop_name]
        
        if prop_type == "rich_text":
            rich_texts = prop.get("rich_text", [])
            if rich_texts:
                return rich_texts[0].get("plain_text", "")
            return ""
        elif prop_type == "title":
            titles = prop.get("title", [])
            if titles:
                return titles[0].get("plain_text", "")
            return ""
        elif prop_type == "select" and sub_field:
            select = prop.get("select")
            return select.get(sub_field) if select else None
        elif prop_type == "multi_select":
            return prop.get("multi_select", [])
        return None
    except (IndexError, KeyError, TypeError):
        return None

def get_notion_page(page_id):
    """从Notion API获取页面详细信息"""
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Failed to get Notion page", extra={
            "error": str(e),
            "page_id": page_id
        })
        return None

def update_notion_page_issue_id(page_id, issue_id):
    """更新Notion页面的Issue ID字段"""
    try:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {
            "properties": {
                "Issue ID": {
                    "rich_text": [{
                        "text": {
                            "content": issue_id
                        }
                    }]
                }
            }
        }
        resp = requests.patch(url, headers=headers, json=payload)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to update Notion page", extra={
            "error": str(e),
            "page_id": page_id
        })
        return False

def create_gitee_issue(owner, repo, issue_data):
    """创建Gitee Issue"""
    try:
        url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/issues"
        headers2 = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"token {os.getenv('GITEE_ACCESS_TOKEN')}"
        }
        resp = requests.post(url, headers=headers2, json=issue_data)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Failed to create Gitee issue", extra={
            "error": str(e),
            "owner": owner,
            "repo": repo
        })
        return None

if __name__ == "__main__":
    logger.info(f"Starting server on {config['HOST']}:{config['PORT']}")
    app.run(host=config["HOST"], port=config["PORT"])