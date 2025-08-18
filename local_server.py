#!/usr/bin/env python3
"""
本地 GitHub-Notion 同步服务器
用于验证系统功能和提供临时服务
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import hashlib
import hmac
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, Any
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="GitHub-Notion Sync Service", description="本地运行的 GitHub-Notion 双向同步服务", version="1.0.0")

# 配置
GITHUB_WEBHOOK_SECRET = "7a0f7d8a1b968a26275206e7ded245849207a302651eed1ef5b965dad931c518"
DB_FILE = "local_sync.db"


def init_local_db():
    """初始化本地数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建事件表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE,
            source TEXT,
            event_type TEXT,
            payload TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processed'
        )
    """
    )

    conn.commit()
    conn.close()
    logger.info("本地数据库初始化完成")


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """验证 GitHub webhook 签名"""
    if not signature:
        return False

    try:
        expected_signature = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

        if signature.startswith("sha256="):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"签名验证失败: {e}")
        return False


def save_event(event_id: str, source: str, event_type: str, payload: dict):
    """保存事件到本地数据库"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO sync_events 
            (event_id, source, event_type, payload) 
            VALUES (?, ?, ?, ?)
        """,
            (event_id, source, event_type, json.dumps(payload)),
        )

        conn.commit()
        conn.close()
        logger.info(f"事件已保存: {event_id}")
    except Exception as e:
        logger.error(f"保存事件失败: {e}")


async def process_github_issue(payload: dict):
    """处理 GitHub Issue 事件"""
    try:
        action = payload.get("action", "")
        issue = payload.get("issue", {})

        logger.info(f"处理 GitHub Issue: {action}")
        logger.info(f"Issue 标题: {issue.get('title', 'Unknown')}")
        logger.info(f"Issue 编号: {issue.get('number', 'Unknown')}")

        # 模拟 Notion 同步
        await asyncio.sleep(1)  # 模拟处理时间
        logger.info("✅ 模拟 Notion 同步完成")

        return True
    except Exception as e:
        logger.error(f"处理 GitHub Issue 失败: {e}")
        return False


@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "GitHub-Notion 同步服务",
        "status": "running",
        "mode": "local",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    # 检查数据库
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sync_events")
        event_count = cursor.fetchone()[0]
        conn.close()
        db_status = "ok"
    except Exception as e:
        event_count = 0
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": "local",
        "app_info": {"app": "github-notion-sync", "version": "1.0.0", "mode": "local"},
        "checks": {
            "database": {"status": db_status, "events_count": event_count},
            "github_webhook": {"status": "configured", "secret_configured": bool(GITHUB_WEBHOOK_SECRET)},
        },
    }


@app.get("/metrics")
async def metrics():
    """监控指标端点"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sync_events")
        total_events = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sync_events WHERE status = 'processed'")
        processed_events = cursor.fetchone()[0]

        conn.close()
    except Exception:
        total_events = 0
        processed_events = 0

    return {
        "service": "github-notion-sync",
        "mode": "local",
        "events": {"total": total_events, "processed": processed_events},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/github_webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """GitHub webhook 端点"""
    try:
        # 获取请求体
        body = await request.body()
        payload = await request.json()

        # 获取头部信息
        signature = request.headers.get("X-Hub-Signature-256", "")
        event_type = request.headers.get("X-GitHub-Event", "")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")

        logger.info(f"收到 GitHub webhook: {event_type}")

        # 验证签名
        if not verify_github_signature(body, signature):
            logger.warning("GitHub webhook 签名验证失败")
            raise HTTPException(status_code=403, detail="Invalid signature")

        # 保存事件
        event_id = f"github:{delivery_id}"
        save_event(event_id, "github", event_type, payload)

        # 后台处理事件
        if event_type == "issues":
            background_tasks.add_task(process_github_issue, payload)

        logger.info(f"✅ GitHub webhook 处理成功: {event_id}")

        return {"message": "ok", "event_id": event_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理 GitHub webhook 失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/events")
async def get_events():
    """获取事件列表"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT event_id, source, event_type, processed_at, status 
            FROM sync_events 
            ORDER BY processed_at DESC 
            LIMIT 50
        """
        )

        events = []
        for row in cursor.fetchall():
            events.append(
                {"event_id": row[0], "source": row[1], "event_type": row[2], "processed_at": row[3], "status": row[4]}
            )

        conn.close()

        return {"events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"获取事件列表失败: {e}")
        raise HTTPException(status_code=500, detail="Database error")


def main():
    """主函数"""
    print("🚀 启动本地 GitHub-Notion 同步服务...")

    # 初始化数据库
    init_local_db()

    # 启动服务器
    print("🌐 服务地址: http://localhost:8000")
    print("🏥 健康检查: http://localhost:8000/health")
    print("📊 监控指标: http://localhost:8000/metrics")
    print("📋 事件列表: http://localhost:8000/events")
    print("🔗 GitHub Webhook: http://localhost:8000/github_webhook")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
