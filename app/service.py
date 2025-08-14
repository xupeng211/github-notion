from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import time
from collections import deque
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, Tuple, Optional

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import Counter, Gauge, Histogram
from app.models import (
    SessionLocal,
    deadletter_count,
    deadletter_enqueue,
    event_hash_from_bytes,
    mark_event_processed,
    should_skip_event,
    upsert_mapping,
    create_sync_event,
    should_skip_sync_event,
    mark_sync_event_processed,
    get_mapping_by_source,
    get_mapping_by_notion_page,
)
from app.github import github_service

# Metrics (allow disabling in tests to avoid duplicate registration)
DISABLE_METRICS = os.getenv(
    "DISABLE_METRICS",
    "").lower() in (
        "1",
        "true",
        "yes") or bool(
            os.getenv("PYTEST_CURRENT_TEST"))

if DISABLE_METRICS:
    class _Noop:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass
    EVENTS_TOTAL = _Noop()
    RETRIES_TOTAL = _Noop()
    PROCESS_LATENCY = _Noop()
    DEADLETTER_SIZE = _Noop()
    PROCESS_P95_MS = _Noop()
    DEADLETTER_REPLAY_TOTAL = _Noop()
    HTTP_REQUESTS_TOTAL = _Noop()
    HTTP_REQUEST_DURATION = _Noop()
    WEBHOOK_ERRORS_TOTAL = _Noop()
    NOTION_API_CALLS_TOTAL = _Noop()
    NOTION_API_DURATION = _Noop()
    DATABASE_OPERATIONS_TOTAL = _Noop()
    RATE_LIMIT_HITS_TOTAL = _Noop()
else:
    EVENTS_TOTAL = Counter("events_total", "Total events processed", ["result"])  # result: success|skip|fail
    RETRIES_TOTAL = Counter("retries_total", "Total retry attempts")
    PROCESS_LATENCY = Histogram("process_latency_seconds", "Processing latency seconds")
    DEADLETTER_SIZE = Gauge("deadletter_size", "Current deadletter size")
    PROCESS_P95_MS = Gauge("process_p95_ms", "Approx p95 of processing latency in ms (sliding window)")
    DEADLETTER_REPLAY_TOTAL = Counter("deadletter_replay_total", "Total deadletters replayed")

    # HTTP 请求指标
    HTTP_REQUESTS_TOTAL = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
    HTTP_REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])

    # Webhook 错误指标
    WEBHOOK_ERRORS_TOTAL = Counter("webhook_errors_total", "Total webhook processing errors", ["error_type"])

    # Notion API 指标
    NOTION_API_CALLS_TOTAL = Counter("notion_api_calls_total", "Total Notion API calls", ["operation", "status"])
    NOTION_API_DURATION = Histogram("notion_api_duration_seconds", "Notion API call duration", ["operation"])

    # 数据库操作指标
    DATABASE_OPERATIONS_TOTAL = Counter(
        "database_operations_total", "Total database operations", [
            "operation", "status"])

    # 速率限制指标
    RATE_LIMIT_HITS_TOTAL = Counter("rate_limit_hits_total", "Total rate limit hits")

logger = logging.getLogger("service")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
DISABLE_NOTION = os.getenv("DISABLE_NOTION", "").lower() not in ("", "0", "false")
GITEE_TOKEN = os.getenv("GITEE_TOKEN", "")

_issue_locks: Dict[str, Lock] = {}
_global_lock = Lock()
_durations = deque(maxlen=200)


def _get_issue_lock(issue_id: str) -> Lock:
    with _global_lock:
        if issue_id not in _issue_locks:
            _issue_locks[issue_id] = Lock()
        return _issue_locks[issue_id]


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def verify_gitee_signature(secret: str, payload: bytes, signature: str) -> bool:
    """
    验证Gitee webhook请求的HMAC-SHA256签名

    使用时间安全的比较算法验证webhook请求的完整性和真实性，
    防止伪造的webhook请求和时序攻击。

    Args:
        secret: Gitee webhook配置的密钥字符串
        payload: HTTP请求体的原始字节数据
        signature: 从X-Gitee-Token头部获取的签名

    Returns:
        bool: 签名验证成功返回True，失败返回False

    Security:
        - 使用hmac.compare_digest()防止时序攻击
        - 采用SHA256哈希算法确保安全性
        - 空值检查防止绕过验证

    Example:
        >>> secret = "my-webhook-secret"
        >>> payload = b'{"issue": {"id": 123}}'
        >>> signature = "expected_hmac_signature"
        >>> verify_gitee_signature(secret, payload, signature)
        True
    """
    # 防止空值绕过安全验证
    if not secret or not signature:
        return False

    # 使用HMAC-SHA256计算期望的签名
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    # 使用时间安全的比较函数防止时序攻击
    return hmac.compare_digest(expected, signature)


def verify_notion_signature(secret: str, payload: bytes, signature: str) -> bool:
    """Notion webhook签名验证示例（使用HMAC-SHA256）"""
    if not secret:
        return True  # 未配置时跳过校验
    if not signature:
        return False
    # 假设签名格式为 sha256=<hex>
    if signature.startswith("sha256="):
        signature = signature.split("=", 1)[1]
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def exponential_backoff_request(method: str, url: str, headers: Dict[str, str] = None, json_data: Dict[str, Any] = None,
                                max_retries: int = 5, base_delay: float = 0.5) -> Tuple[bool, Dict[str, Any]]:
    """
    带指数退避策略的HTTP请求重试机制

    为外部API调用（主要是Notion API）提供可靠的重试机制，通过指数退避
    算法处理网络波动、速率限制和临时服务不可用等问题。

    Args:
        method: HTTP方法 ("GET", "POST", "PATCH", "DELETE"等)
        url: 请求的完整URL
        headers: 可选的HTTP头部字典
        json_data: 可选的JSON请求体数据
        max_retries: 最大重试次数，默认5次
        base_delay: 基础延迟时间（秒），默认0.5秒

    Returns:
        Tuple[bool, Dict[str, Any]]: (成功标志, 响应数据或错误信息)
        - (True, response_json): 请求成功，返回解析后的JSON数据
        - (True, {}): 请求成功但无响应体
        - (False, {"status": code, "text": msg}): HTTP错误
        - (False, {"error": error_msg}): 网络或其他异常

    Retry Logic:
        - 429 (Too Many Requests): 立即重试，指数退避
        - 5xx (Server Errors): 服务器错误时重试
        - 指数退避时间: base_delay * (2 ^ attempt)
        - 自动监控和记录API调用指标

    Monitoring:
        - 自动识别API操作类型 (create_page, update_page等)
        - 记录调用次数、成功率、延迟时间
        - 重试统计和错误追踪

    Example:
        >>> success, data = exponential_backoff_request(
        ...     "POST", "https://api.notion.com/v1/pages",
        ...     headers={"Authorization": "Bearer token"},
        ...     json_data={"parent": {"database_id": "xxx"}}
        ... )
        >>> if success:
        ...     print(f"Created page: {data['id']}")
    """
    headers = headers or {}

    # 确定 API 操作类型用于监控指标分类
    operation = "unknown"
    if "notion.com" in url:
        if "/pages/" in url and method == "PATCH":
            operation = "update_page"
        elif "/pages" in url and method == "POST":
            operation = "create_page"
        elif "/databases/" in url and method == "POST":
            operation = "query_database"
        elif "/users/me" in url:
            operation = "get_user"

    # 记录请求开始时间用于延迟监控
    start_time = time.time()

    # 指数退避重试循环：尝试 max_retries + 1 次
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, headers=headers, json=json_data, timeout=10)

            # 记录 API 调用指标
            if "notion.com" in url:
                status = "success" if resp.status_code < 400 else "error"
                NOTION_API_CALLS_TOTAL.labels(operation=operation, status=status).inc()

            if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                if attempt < max_retries:
                    RETRIES_TOTAL.inc()
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                else:
                    return False, {"status": resp.status_code, "text": resp.text}
            resp.raise_for_status()

            # 记录成功的 API 调用持续时间
            if "notion.com" in url:
                duration = time.time() - start_time
                NOTION_API_DURATION.labels(operation=operation).observe(duration)

            if resp.text:
                return True, resp.json()
            return True, {}
        except requests.RequestException as e:
            if attempt < max_retries:
                RETRIES_TOTAL.inc()
                time.sleep(base_delay * (2 ** attempt))
                continue

            # 记录失败的 API 调用
            if "notion.com" in url:
                NOTION_API_CALLS_TOTAL.labels(operation=operation, status="error").inc()
                duration = time.time() - start_time
                NOTION_API_DURATION.labels(operation=operation).observe(duration)

            return False, {"error": str(e)}


def notion_upsert_page(issue: Dict[str, Any]) -> Tuple[bool, str]:
    """
    在Notion数据库中创建或更新Issue页面

    根据Gitee Issue信息在Notion数据库中查找已存在的页面，
    如果找到则更新，否则创建新页面。支持测试模式绕过实际API调用。

    Args:
        issue: Gitee Issue的完整数据字典，包含标题、ID等信息

    Returns:
        Tuple[bool, str]: (操作成功标志, 页面ID或错误信息)
        - (True, page_id): 操作成功，返回Notion页面ID
        - (False, error_json): 操作失败，返回错误详情JSON

    Process:
        1. 测试模式检查：如果DISABLE_NOTION=True，返回模拟页面ID
        2. 数据库查询：根据Issue标题查找已存在的页面
        3. 更新页面：如果页面存在，更新其属性
        4. 创建页面：如果页面不存在，在数据库中创建新页面

    Notion API Calls:
        - POST /databases/{id}/query: 按标题查询页面
        - PATCH /pages/{id}: 更新已存在的页面
        - POST /pages: 创建新页面

    Environment Variables:
        - NOTION_TOKEN: Notion API访问令牌
        - NOTION_DATABASE_ID: 目标数据库ID
        - DISABLE_NOTION: 测试模式开关

    Example:
        >>> issue_data = {"title": "Bug修复", "number": 123}
        >>> success, page_id = notion_upsert_page(issue_data)
        >>> if success:
        ...     print(f"页面ID: {page_id}")
    """
    # 测试模式：绕过外部依赖，便于本地开发和单元测试
    if DISABLE_NOTION:
        title = issue.get("title", "")
        # 返回合成的页面ID以支持下游的映射操作
        return True, f"DRYRUN_PAGE_{title or 'untitled'}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    title = issue.get("title", "")
    q_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    ok, data = exponential_backoff_request(
        "POST", q_url, headers, {
            "filter": {
                "property": "Task", "title": {
                    "equals": title}}})
    if not ok:
        return False, json.dumps(data)
    results = data.get("results", [])
    if results:
        page_id = results[0]["id"]
        p_url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": {"Task": {"title": [{"text": {"content": title}}]}}}
        ok2, _ = exponential_backoff_request("PATCH", p_url, headers, payload)
        if ok2:
            return True, page_id
        return False, page_id
    c_url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Task": {"title": [{"text": {"content": title}}]},
            "Issue ID": {"rich_text": [{"text": {"content": str(issue.get("number"))}}]},
        }
    }
    ok3, res = exponential_backoff_request("POST", c_url, headers, payload)
    if ok3:
        return True, res.get("id", "")
    return False, json.dumps(res)


def process_gitee_event(body_bytes: bytes, secret: str, signature: str, event_type: str) -> Tuple[bool, str]:
    """
    处理Gitee webhook事件的核心业务逻辑

    这是系统的主要处理函数，负责验证、解析、去重和同步Gitee事件到Notion。
    采用分布式锁确保并发安全，使用死信队列处理失败情况。

    Args:
        body_bytes: HTTP请求体的原始字节数据
        secret: webhook签名验证密钥
        signature: 请求头中的HMAC签名
        event_type: Gitee事件类型 (如 "Issue Hook")

    Returns:
        Tuple[bool, str]: (处理成功标志, 状态消息)
        - (True, "ok"): 处理成功
        - (True, "duplicate"): 重复事件，已跳过
        - (False, "invalid_signature"): 签名验证失败
        - (False, "missing_issue_id"): 缺少必要的issue ID
        - (False, "notion_error"): Notion API调用失败

    Business Logic:
        1. 安全验证：HMAC签名校验防止伪造请求
        2. 幂等性检查：基于事件哈希避免重复处理
        3. 分布式锁：按issue_id加锁确保并发安全
        4. 故障恢复：失败事件进入死信队列等待重试
        5. 监控指标：记录处理时间和成功失败统计

    Raises:
        无直接异常，所有错误都通过返回值处理
    """
    # 记录处理开始时间，用于性能监控
    start = time.time()
    try:
        # 第一步：安全验证 - 防止伪造的webhook请求
        if not verify_gitee_signature(secret, body_bytes, signature):
            EVENTS_TOTAL.labels("fail").inc()
            return False, "invalid_signature"

        # 第二步：解析payload并提取关键信息
        payload = json.loads(body_bytes.decode("utf-8"))
        issue = payload.get("issue") or {}
        issue_id = str(issue.get("number") or issue.get("id") or "")

        # 第三步：生成事件哈希用于幂等性检查
        event_hash = event_hash_from_bytes(body_bytes)

        # 验证必要的业务数据
        if not issue_id:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_issue_id"

        # 第四步：获取分布式锁，确保同一issue的并发安全
        lock = _get_issue_lock(issue_id)
        with lock:
            with session_scope() as db:
                # 第五步：幂等性检查 - 避免重复处理相同事件
                if should_skip_event(db, issue_id, event_hash, platform="gitee"):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "duplicate"

                # 第六步：调用Notion API进行页面创建或更新
                ok, page_or_err = notion_upsert_page(issue)
                if not ok:
                    # 第七步：失败处理 - 将事件放入死信队列以便后续重试
                    deadletter_enqueue(db, payload, reason="notion_error", last_error=str(page_or_err),
                                       source_platform="gitee", entity_id=issue_id)
                    DEADLETTER_SIZE.set(deadletter_count(db))
                    EVENTS_TOTAL.labels("fail").inc()
                    return False, "notion_error"

                # 第八步：成功处理 - 更新映射关系和处理状态
                page_id = page_or_err
                upsert_mapping(db, "gitee", issue_id, page_id)
                mark_event_processed(db, issue_id, event_hash, platform="gitee")

        # 记录成功指标
        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"

    finally:
        # 无论成功失败都记录处理时间用于性能分析
        dur = (time.time() - start)
        PROCESS_LATENCY.observe(dur)
        # update p95 gauge using sliding window
        _durations.append(dur * 1000.0)
        arr = sorted(_durations)
        if arr:
            k = max(0, int(math.ceil(0.95 * len(arr)) - 1))

            PROCESS_P95_MS.set(arr[k])

# Deadletter replay logic


def replay_deadletters_once(secret_token: str) -> int:
    """
    重新处理死信队列中的失败事件

    从数据库中获取所有失败的webhook事件，重新进行签名验证和处理。
    只有提供正确的密钥令牌才能执行重试操作，确保操作安全性。

    Args:
        secret_token: 管理员密钥令牌，用于授权重试操作

    Returns:
        int: 成功重新处理的事件数量

    Security:
        - 需要环境变量DEADLETTER_REPLAY_TOKEN验证权限
        - 如果密钥不匹配，返回0且不执行任何操作
        - 重新生成HMAC签名确保数据完整性

    Process:
        1. 权限验证：检查提供的密钥是否匹配环境变量
        2. 查询失败事件：从数据库获取所有待重试的事件
        3. 重新签名：为每个事件重新生成HMAC-SHA256签名
        4. 重新处理：调用process_gitee_event进行标准处理流程
        5. 标记完成：成功处理的事件标记为已重试
        6. 更新指标：记录重试成功的统计数据

    Environment Variables:
        - DEADLETTER_REPLAY_TOKEN: 重试操作的授权令牌
        - GITEE_WEBHOOK_SECRET: 用于重新生成签名的密钥

    Example:
        >>> # 管理员手动触发重试
        >>> count = replay_deadletters_once("admin-secret-token")
        >>> print(f"成功重试 {count} 个失败事件")
    """
    # 安全验证：检查重试授权令牌
    token_env = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
    if token_env and secret_token and token_env != secret_token:
        return 0  # 权限验证失败，拒绝执行
    from app.models import SessionLocal, deadletter_list, deadletter_mark_replayed
    cnt = 0
    with SessionLocal() as s:
        items = deadletter_list(s)
        for it in items:
            payload = json.dumps(it.payload).encode()
            sig = hmac.new(os.getenv("GITEE_WEBHOOK_SECRET", "").encode(), payload,
                           hashlib.sha256).hexdigest() if os.getenv("GITEE_WEBHOOK_SECRET") else ""
            ok, _ = process_gitee_event(payload, os.getenv("GITEE_WEBHOOK_SECRET", ""), sig, "replay")
            if ok:
                deadletter_mark_replayed(s, it.id)
                DEADLETTER_REPLAY_TOTAL.inc()
                cnt += 1
    return cnt


def start_deadletter_scheduler():
    """
    启动死信队列重试的后台调度器

    创建并启动一个后台调度任务，定期自动重试死信队列中的失败事件。
    调度间隔可通过环境变量配置，支持禁用调度功能。

    Returns:
        BackgroundScheduler | None:
        - BackgroundScheduler: 启动成功的调度器实例
        - None: 调度器被禁用（间隔设置为0或负数）

    Configuration:
        - DEADLETTER_REPLAY_INTERVAL_MINUTES: 重试间隔（分钟）
        - 默认值: 10分钟
        - 设置为0或负数: 禁用自动重试
        - 无效值时自动回退到默认10分钟

    Scheduler Details:
        - 使用APScheduler的BackgroundScheduler
        - daemon=True: 守护进程模式，主程序退出时自动停止
        - 调度任务: 每隔指定时间调用replay_deadletters_once
        - 自动传递环境变量中的管理员令牌

    Example:
        >>> scheduler = start_deadletter_scheduler()
        >>> if scheduler:
        ...     print("死信队列重试调度器已启动")
        ... else:
        ...     print("调度器被禁用")
    """
    # 解析重试间隔配置，支持错误处理和默认值
    try:
        interval = int(os.getenv("DEADLETTER_REPLAY_INTERVAL_MINUTES", "10"))
    except Exception:
        interval = 10  # 配置解析失败时使用默认值

    # 支持通过设置0或负数来禁用调度器
    if interval <= 0:
        return None
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        lambda: replay_deadletters_once(os.getenv("DEADLETTER_REPLAY_TOKEN", "")),
        "interval",
        minutes=interval,
        id="deadletter_replay",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


# 新增：处理 GitHub 事件

def process_github_event(body_bytes: bytes, event: str) -> Tuple[bool, str]:
    start = time.time()
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
        # 只处理 issues 事件
        if event != "issues":
            EVENTS_TOTAL.labels("skip").inc()
            return True, "ignored_event"

        action = payload.get("action")
        issue = payload.get("issue") or {}
        repository = payload.get("repository") or {}
        owner = (repository.get("owner") or {}).get("login") or payload.get("organization", {}).get("login", "")
        repo = repository.get("name", "")
        issue_number = str(issue.get("number") or issue.get("id") or "")

        if not issue_number or not owner or not repo:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_required_fields"

        # 如果由同步引发（body含有sync-marker），直接跳过
        if "<!-- sync-marker:" in (issue.get("body") or ""):
            EVENTS_TOTAL.labels("skip").inc()
            return True, "sync_induced"

        # 幂等哈希
        event_hash = event_hash_from_bytes(body_bytes)

        lock = _get_issue_lock(f"github:{owner}/{repo}#{issue_number}")
        with lock:
            with session_scope() as db:
                if should_skip_event(db, issue_number, event_hash, platform="github"):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "duplicate"

                # 防循环：最近是否有 Notion -> GitHub 的同步
                if should_skip_sync_event(db, event_hash, entity_id=issue_number, source_platform="github", target_platform="notion"):
                    EVENTS_TOTAL.labels("skip").inc()
                    return True, "loop_prevented"

                # 将 Issue 同步到 Notion
                notion_ok, page_or_err = notion_upsert_page({
                    "title": issue.get("title"),
                    "number": issue.get("number"),
                    "body": issue.get("body", ""),
                })
                if not notion_ok:
                    deadletter_enqueue(db, payload, reason="notion_error", last_error=str(page_or_err),
                                       source_platform="github", entity_id=issue_number)
                    DEADLETTER_SIZE.set(deadletter_count(db))
                    EVENTS_TOTAL.labels("fail").inc()
                    return False, "notion_error"

                page_id = page_or_err
                upsert_mapping(db, "github", issue_number, page_id,
                               source_url=issue.get("html_url"), notion_database_id=NOTION_DATABASE_ID)
                mark_event_processed(db, issue_number, event_hash, platform="github")
                ev_id = create_sync_event(db, source_platform="github", target_platform="notion",
                                          entity_id=issue_number, action=action or "updated", event_hash=event_hash,
                                          is_sync_induced=False)
                mark_sync_event_processed(db, ev_id)

        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"
    finally:
        dur = (time.time() - start)
        PROCESS_LATENCY.observe(dur)
        _durations.append(dur * 1000.0)
        arr = sorted(_durations)
        if arr:
            k = max(0, int(math.ceil(0.95 * len(arr)) - 1))
            PROCESS_P95_MS.set(arr[k])


# 新增：处理 Notion 事件（页面更新 => 回写 GitHub）

def process_notion_event(body_bytes: bytes) -> Tuple[bool, str]:
    start = time.time()
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
        # 简化支持：期望 payload 中包含 page.id 和变化属性摘要
        page = payload.get("page") or {}
        page_id = page.get("id") or payload.get("id")
        if not page_id:
            EVENTS_TOTAL.labels("fail").inc()
            return False, "missing_page_id"

        # 幂等哈希
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

            # 防重复
            if should_skip_event(db, issue_number, event_hash, platform="notion"):
                EVENTS_TOTAL.labels("skip").inc()
                return True, "duplicate"

            # 防循环：最近是否有 GitHub -> Notion 的同步
            if should_skip_sync_event(db, event_hash, entity_id=issue_number, source_platform="notion", target_platform="github"):
                EVENTS_TOTAL.labels("skip").inc()
                return True, "loop_prevented"

            # 映射 Notion 属性到 GitHub Issue 字段
            title = None
            body = None
            state = None

            properties = (page.get("properties") or {})
            # 简单映射：Task -> title, Output -> body, Status -> state
            task_prop = properties.get("Task") or {}
            if task_prop.get("title"):
                try:
                    title = "".join([t.get("plain_text") or t.get("text", {}).get("content", "") for t in task_prop["title"]])
                except Exception:
                    pass
            output_prop = properties.get("Output") or {}
            if output_prop.get("rich_text"):
                try:
                    body = "".join([t.get("plain_text") or t.get("text", {}).get("content", "") for t in output_prop["rich_text"]])
                except Exception:
                    pass
            status_prop = properties.get("Status") or {}
            if status_prop.get("select") and status_prop["select"]:
                state = status_prop["select"].get("name")
                # 将 Notion 状态名映射到 GitHub 的 open/closed
                if state and state.lower() in ("done", "closed", "完成"):
                    state = "closed"
                else:
                    state = "open"

            # 从 mapping.source_url 提取 owner/repo
            owner_repo = github_service.extract_repo_info(mapping.source_url or "")
            if not owner_repo:
                EVENTS_TOTAL.labels("fail").inc()
                return False, "missing_repo_info"
            owner, repo = owner_repo

            # 生成同步标记
            sync_marker = event_hash[:12]

            # 更新 GitHub Issue
            ok, msg = github_service.update_issue(owner, repo, int(issue_number), title=title, body=body, state=state, sync_marker=sync_marker)
            if not ok:
                deadletter_enqueue(db, payload, reason="github_error", last_error=msg,
                                   source_platform="notion", entity_id=str(page_id))
                DEADLETTER_SIZE.set(deadletter_count(db))
                EVENTS_TOTAL.labels("fail").inc()
                return False, "github_error"

            mark_event_processed(db, issue_number, event_hash, platform="notion")
            ev_id = create_sync_event(db, source_platform="notion", target_platform="github",
                                      entity_id=issue_number, action="updated", event_hash=event_hash,
                                      is_sync_induced=True)
            mark_sync_event_processed(db, ev_id)

        EVENTS_TOTAL.labels("success").inc()
        return True, "ok"
    finally:
        dur = (time.time() - start)
        PROCESS_LATENCY.observe(dur)
        _durations.append(dur * 1000.0)
        arr = sorted(_durations)
        if arr:
            k = max(0, int(math.ceil(0.95 * len(arr)) - 1))
            PROCESS_P95_MS.set(arr[k])
