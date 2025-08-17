"""
实时问题检测系统
监控运行时环境，及时发现潜在问题
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session


@dataclass
class Alert:
    """告警信息"""

    id: str
    level: str  # 'info', 'warning', 'error', 'critical'
    category: str
    title: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class HealthMetric:
    """健康指标"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


class RealtimeMonitor:
    """实时监控器"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.alerts = deque(maxlen=1000)
        self.metrics = defaultdict(lambda: deque(maxlen=100))
        self.checkers = []
        self.alert_handlers = []
        self.logger = logging.getLogger(__name__)

        # 注册默认检查器
        self._register_default_checkers()

    def _register_default_checkers(self):
        """注册默认检查器"""
        self.checkers = [
            self._check_database_compatibility,
            self._check_environment_consistency,
            self._check_performance_metrics,
            self._check_error_rates,
            self._check_resource_usage,
            self._check_configuration_drift,
        ]

    def start(self):
        """启动监控"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Realtime monitor started")

    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Realtime monitor stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._run_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(self.check_interval)

    def _run_checks(self):
        """运行所有检查"""
        for checker in self.checkers:
            try:
                checker()
            except Exception as e:
                self._create_alert(
                    level="error",
                    category="monitor",
                    title=f"Checker failed: {checker.__name__}",
                    description=str(e),
                    metadata={"checker": checker.__name__, "error": str(e)},
                )

    def _check_database_compatibility(self):
        """检查数据库兼容性"""
        try:
            from app.models import SessionLocal

            with SessionLocal() as db:
                inspector = inspect(db.bind)

                # 检查关键表是否存在
                required_tables = ["processed_event", "sync_event"]
                missing_tables = []

                existing_tables = inspector.get_table_names()
                for table in required_tables:
                    if table not in existing_tables:
                        missing_tables.append(table)

                if missing_tables:
                    self._create_alert(
                        level="critical",
                        category="database",
                        title="Missing database tables",
                        description=f"Required tables not found: {', '.join(missing_tables)}",
                        metadata={"missing_tables": missing_tables},
                    )

                # 检查字段兼容性
                if "processed_event" in existing_tables:
                    columns = [col["name"] for col in inspector.get_columns("processed_event")]

                    # 记录字段状态
                    has_source_platform = "source_platform" in columns
                    self._record_metric("database_has_source_platform", 1.0 if has_source_platform else 0.0, "boolean")

                    # 如果缺少重要字段，发出警告
                    if not has_source_platform:
                        self._create_alert(
                            level="warning",
                            category="database",
                            title="Database schema compatibility issue",
                            description="processed_event table missing source_platform column",
                            metadata={"table": "processed_event", "missing_column": "source_platform"},
                        )

        except Exception as e:
            self._create_alert(
                level="error",
                category="database",
                title="Database compatibility check failed",
                description=str(e),
                metadata={"error": str(e)},
            )

    def _check_environment_consistency(self):
        """检查环境一致性"""
        import os

        # 检查关键环境变量
        required_vars = ["DB_URL", "LOG_LEVEL", "APP_PORT", "GITEE_WEBHOOK_SECRET", "GITHUB_WEBHOOK_SECRET"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self._create_alert(
                level="warning",
                category="environment",
                title="Missing environment variables",
                description=f"Required environment variables not set: {', '.join(missing_vars)}",
                metadata={"missing_vars": missing_vars},
            )

        # 检查PYTHONPATH
        python_path = os.getenv("PYTHONPATH", "")
        if "app" not in python_path:
            self._create_alert(
                level="warning",
                category="environment",
                title="PYTHONPATH configuration issue",
                description="PYTHONPATH may not include app directory",
                metadata={"current_pythonpath": python_path},
            )

        # 记录环境指标
        self._record_metric("environment_vars_count", len([v for v in required_vars if os.getenv(v)]), "count")

    def _check_performance_metrics(self):
        """检查性能指标"""
        import psutil

        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self._record_metric("cpu_usage_percent", cpu_percent, "percent", 80.0, 95.0)

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        self._record_metric("memory_usage_percent", memory_percent, "percent", 80.0, 95.0)

        # 磁盘使用率
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        self._record_metric("disk_usage_percent", disk_percent, "percent", 85.0, 95.0)

        # 检查阈值
        if cpu_percent > 95:
            self._create_alert(
                level="critical",
                category="performance",
                title="High CPU usage",
                description=f"CPU usage is {cpu_percent:.1f}%",
                metadata={"cpu_percent": cpu_percent},
            )
        elif cpu_percent > 80:
            self._create_alert(
                level="warning",
                category="performance",
                title="Elevated CPU usage",
                description=f"CPU usage is {cpu_percent:.1f}%",
                metadata={"cpu_percent": cpu_percent},
            )

    def _check_error_rates(self):
        """检查错误率"""
        try:
            # 这里应该从日志或指标系统获取错误率
            # 暂时使用模拟数据

            # 检查最近的错误日志
            error_count = self._count_recent_errors()
            self._record_metric("error_count_per_minute", error_count, "count", 5.0, 20.0)

            if error_count > 20:
                self._create_alert(
                    level="critical",
                    category="errors",
                    title="High error rate",
                    description=f"Error rate: {error_count} errors/minute",
                    metadata={"error_count": error_count},
                )
            elif error_count > 5:
                self._create_alert(
                    level="warning",
                    category="errors",
                    title="Elevated error rate",
                    description=f"Error rate: {error_count} errors/minute",
                    metadata={"error_count": error_count},
                )

        except Exception as e:
            self.logger.error(f"Error rate check failed: {e}")

    def _check_resource_usage(self):
        """检查资源使用情况"""
        try:
            # 检查数据库连接数
            from app.models import SessionLocal

            with SessionLocal() as db:
                # 模拟检查活跃连接数
                active_connections = self._get_active_connections(db)
                self._record_metric("database_connections", active_connections, "count", 80.0, 100.0)

                if active_connections > 100:
                    self._create_alert(
                        level="critical",
                        category="resources",
                        title="Too many database connections",
                        description=f"Active connections: {active_connections}",
                        metadata={"connection_count": active_connections},
                    )

        except Exception as e:
            self.logger.error(f"Resource usage check failed: {e}")

    def _check_configuration_drift(self):
        """检查配置漂移"""
        try:
            # 检查关键配置是否发生变化
            self._get_current_config()

            # 与基线配置比较（这里需要实现配置基线存储）
            # baseline_config = self._get_baseline_config()

            # 暂时记录当前配置状态
            self._record_metric("config_check_timestamp", time.time(), "timestamp")

        except Exception as e:
            self.logger.error(f"Configuration drift check failed: {e}")

    def _count_recent_errors(self) -> int:
        """统计最近的错误数量"""
        # 这里应该实现实际的错误统计逻辑
        # 可以从日志文件、数据库或监控系统获取
        return 0

    def _get_active_connections(self, db: Session) -> int:
        """获取活跃数据库连接数"""
        # 这里应该实现实际的连接数查询
        # 不同数据库有不同的查询方式
        return 1

    def _get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        import os

        return {
            "db_url": os.getenv("DB_URL", ""),
            "log_level": os.getenv("LOG_LEVEL", ""),
            "app_port": os.getenv("APP_PORT", ""),
            "disable_notion": os.getenv("DISABLE_NOTION", ""),
        }

    def _record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        threshold_warning: Optional[float] = None,
        threshold_critical: Optional[float] = None,
    ):
        """记录指标"""
        metric = HealthMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical,
        )

        self.metrics[name].append(metric)

        # 检查阈值
        if threshold_critical and value >= threshold_critical:
            self._create_alert(
                level="critical",
                category="metrics",
                title=f"Critical threshold exceeded: {name}",
                description=f"{name} is {value} {unit} (threshold: {threshold_critical})",
                metadata={"metric": name, "value": value, "threshold": threshold_critical},
            )
        elif threshold_warning and value >= threshold_warning:
            self._create_alert(
                level="warning",
                category="metrics",
                title=f"Warning threshold exceeded: {name}",
                description=f"{name} is {value} {unit} (threshold: {threshold_warning})",
                metadata={"metric": name, "value": value, "threshold": threshold_warning},
            )

    def _create_alert(self, level: str, category: str, title: str, description: str, metadata: Dict[str, Any] = None):
        """创建告警"""
        alert_id = f"{category}_{int(time.time())}_{hash(title) % 10000}"

        alert = Alert(
            id=alert_id,
            level=level,
            category=category,
            title=title,
            description=description,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        self.alerts.append(alert)

        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")

        # 记录日志
        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }.get(level, logging.INFO)

        self.logger.log(log_level, f"[{category.upper()}] {title}: {description}")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)

    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """获取最近的告警"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp >= cutoff_time]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {}

        for metric_name, metric_history in self.metrics.items():
            if metric_history:
                latest = metric_history[-1]
                values = [m.value for m in metric_history]

                summary[metric_name] = {
                    "current": latest.value,
                    "unit": latest.unit,
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "last_updated": latest.timestamp.isoformat(),
                }

        return summary

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        recent_alerts = self.get_recent_alerts(1)  # 最近1小时

        critical_alerts = [a for a in recent_alerts if a.level == "critical"]
        warning_alerts = [a for a in recent_alerts if a.level == "warning"]

        if critical_alerts:
            status = "critical"
        elif warning_alerts:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "alerts": {"critical": len(critical_alerts), "warning": len(warning_alerts), "total": len(recent_alerts)},
            "metrics_count": len(self.metrics),
            "uptime_seconds": time.time() - getattr(self, "_start_time", time.time()),
        }


# 告警处理器示例
def console_alert_handler(alert: Alert):
    """控制台告警处理器"""
    print(f"🚨 [{alert.level.upper()}] {alert.title}")
    print(f"   {alert.description}")
    print(f"   Time: {alert.timestamp}")
    if alert.metadata:
        print(f"   Metadata: {alert.metadata}")
    print()


def webhook_alert_handler(webhook_url: str):
    """Webhook告警处理器工厂"""

    def handler(alert: Alert):
        import requests

        payload = {"alert": asdict(alert), "timestamp": alert.timestamp.isoformat()}

        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Failed to send webhook alert: {e}")

    return handler


# 全局监控实例
_global_monitor = None


def get_monitor() -> RealtimeMonitor:
    """获取全局监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = RealtimeMonitor()
    return _global_monitor


def start_monitoring():
    """启动监控"""
    monitor = get_monitor()
    monitor.add_alert_handler(console_alert_handler)
    monitor.start()
    return monitor


def main():
    """命令行工具"""
    import argparse

    parser = argparse.ArgumentParser(description="Realtime Monitor")
    parser.add_argument("command", choices=["start", "status", "alerts", "metrics"])
    parser.add_argument("--interval", "-i", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back for alerts")

    args = parser.parse_args()

    if args.command == "start":
        monitor = RealtimeMonitor(check_interval=args.interval)
        monitor.add_alert_handler(console_alert_handler)
        monitor.start()

        try:
            print(f"Monitor started with {args.interval}s interval. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            monitor.stop()

    elif args.command == "status":
        monitor = get_monitor()
        status = monitor.get_health_status()
        print(json.dumps(status, indent=2))

    elif args.command == "alerts":
        monitor = get_monitor()
        alerts = monitor.get_recent_alerts(args.hours)

        for alert in alerts:
            print(f"[{alert.timestamp}] {alert.level.upper()}: {alert.title}")
            print(f"  {alert.description}")
            if alert.metadata:
                print(f"  Metadata: {alert.metadata}")
            print()

    elif args.command == "metrics":
        monitor = get_monitor()
        metrics = monitor.get_metrics_summary()
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
