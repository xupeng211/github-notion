"""
重试管理器 - 提供指数退避重试机制和死信队列处理
支持自动重试失败的事件，防止数据丢失
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.models import DeadletterQueue, SessionLocal

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略枚举"""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"


@dataclass
class RetryConfig:
    """重试配置"""

    max_attempts: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 300.0  # 最大延迟（秒）
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True  # 是否添加随机抖动
    backoff_multiplier: float = 2.0  # 退避倍数

    # 死信队列配置
    deadletter_enabled: bool = True
    deadletter_ttl: int = 86400 * 7  # 死信保留7天


class RetryableError(Exception):
    """可重试的错误"""


class NonRetryableError(Exception):
    """不可重试的错误"""


class RetryManager:
    """重试管理器"""

    def __init__(self, config: RetryConfig = None, db_session: Optional[Session] = None):
        self.config = config or RetryConfig()
        self.db = db_session or SessionLocal()
        self._should_close_session = db_session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.db.close()

    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间

        Args:
            attempt: 当前重试次数（从1开始）

        Returns:
            延迟时间（秒）
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        else:  # FIXED_INTERVAL
            delay = self.config.base_delay

        # 限制最大延迟
        delay = min(delay, self.config.max_delay)

        # 添加随机抖动
        if self.config.jitter:
            jitter_amount = delay * 0.1  # 10%的抖动
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            error: 发生的错误
            attempt: 当前重试次数

        Returns:
            是否应该重试
        """
        # 检查重试次数限制
        if attempt >= self.config.max_attempts:
            return False

        # 检查错误类型
        if isinstance(error, NonRetryableError):
            return False

        # 对于RetryableError总是重试（在次数限制内）
        if isinstance(error, RetryableError):
            return True

        # 默认的重试逻辑
        retryable_exceptions = [
            # 网络相关错误
            ConnectionError,
            TimeoutError,
            # HTTP相关错误
            Exception,  # 临时简化，实际应该更细化
        ]

        return any(isinstance(error, exc_type) for exc_type in retryable_exceptions)

    async def execute_with_retry(
        self, func: Callable, *args, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """
        使用重试机制执行函数

        Args:
            func: 要执行的函数
            *args: 函数参数
            context: 上下文信息（用于日志和死信队列）
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            最后一次尝试的异常
        """
        last_error = None
        context = context or {}

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.info(
                    "retry_attempt",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self.config.max_attempts,
                        "context": context,
                    },
                )

                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # 成功执行
                if attempt > 1:
                    logger.info(
                        "retry_success",
                        extra={"attempts_used": attempt, "context": context},
                    )

                return result

            except Exception as e:
                last_error = e

                logger.warning(
                    "retry_attempt_failed",
                    extra={
                        "attempt": attempt,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "context": context,
                    },
                )

                # 检查是否应该重试
                if not self.should_retry(e, attempt):
                    logger.error(
                        "retry_abort_no_more_attempts",
                        extra={"attempt": attempt, "error": str(e), "context": context},
                    )
                    break

                # 计算延迟时间
                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logger.info(
                        "retry_delay",
                        extra={
                            "delay_seconds": delay,
                            "next_attempt": attempt + 1,
                            "context": context,
                        },
                    )
                    await asyncio.sleep(delay)

        # 所有重试都失败了
        logger.error(
            "retry_exhausted",
            extra={
                "attempts_made": self.config.max_attempts,
                "final_error": str(last_error),
                "context": context,
            },
        )

        # 发送到死信队列
        if self.config.deadletter_enabled:
            await self._send_to_deadletter(func=func, args=args, kwargs=kwargs, error=last_error, context=context)

        # 抛出最后的错误
        raise last_error

    async def _send_to_deadletter(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        error: Exception,
        context: Dict[str, Any],
    ):
        """
        将失败的任务发送到死信队列

        Args:
            func: 失败的函数
            args: 函数参数
            kwargs: 函数关键字参数
            error: 最后的错误
            context: 上下文信息
        """
        try:
            import pickle

            # 序列化任务数据
            task_data = {
                "function_name": func.__name__,
                "module": func.__module__,
                "args": args,
                "kwargs": kwargs,
                "context": context,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": None,  # 可以添加完整的堆栈跟踪
                },
            }

            payload = pickle.dumps(task_data)

            # 创建死信记录
            deadletter = DeadletterQueue(
                event_type=context.get("event_type", "unknown"),
                provider=context.get("provider", "unknown"),
                error_message=str(error),
                retry_count=self.config.max_attempts,
                payload=payload,
                ttl=int(time.time()) + self.config.deadletter_ttl,
            )

            self.db.add(deadletter)
            self.db.commit()

            logger.info(
                "deadletter_created",
                extra={
                    "deadletter_id": deadletter.id,
                    "error": str(error),
                    "context": context,
                },
            )

        except Exception as deadletter_error:
            logger.error(
                "deadletter_creation_failed",
                extra={
                    "error": str(deadletter_error),
                    "original_error": str(error),
                    "context": context,
                },
            )

    def get_deadletter_stats(self) -> Dict[str, Any]:
        """
        获取死信队列统计信息

        Returns:
            统计信息字典
        """
        try:
            total_count = self.db.query(DeadletterQueue).count()

            # 按提供商统计
            provider_stats = {}
            providers = self.db.query(DeadletterQueue.provider).distinct().all()
            for (provider,) in providers:
                count = self.db.query(DeadletterQueue).filter_by(provider=provider).count()
                provider_stats[provider] = count

            # 按事件类型统计
            event_type_stats = {}
            event_types = self.db.query(DeadletterQueue.event_type).distinct().all()
            for (event_type,) in event_types:
                count = self.db.query(DeadletterQueue).filter_by(event_type=event_type).count()
                event_type_stats[event_type] = count

            return {
                "total_deadletters": total_count,
                "by_provider": provider_stats,
                "by_event_type": event_type_stats,
            }

        except Exception as e:
            logger.error("deadletter_stats_failed", extra={"error": str(e)})
            return {"error": str(e)}


# 便捷的装饰器
def with_retry(config: RetryConfig = None, context: Optional[Dict[str, Any]] = None):
    """
    重试装饰器

    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def my_function():
            # 可能失败的操作
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            retry_manager = RetryManager(config)
            with retry_manager:
                return await retry_manager.execute_with_retry(func, *args, context=context, **kwargs)

        return wrapper

    return decorator


# 预定义的重试配置
RETRY_CONFIGS = {
    "webhook_processing": RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
    "api_calls": RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
    "database_operations": RetryConfig(
        max_attempts=2,
        base_delay=0.5,
        max_delay=5.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    ),
}


# 导出主要类和函数
__all__ = [
    "RetryManager",
    "RetryConfig",
    "RetryStrategy",
    "RetryableError",
    "NonRetryableError",
    "with_retry",
    "RETRY_CONFIGS",
]
