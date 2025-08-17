"""
CI/CD 问题预防体系
统一的预防系统入口
"""

from .adaptive_architecture import (
    AdaptiveQueryBuilder,
    CapabilityRegistry,
    EnvironmentAwareService,
    adaptive_function,
    capability_registry,
)
from .enhanced_precommit import EnhancedPreCommitSystem
from .environment_consistency import EnvironmentConsistencyManager
from .environment_simulator import EnvironmentSimulator, cross_environment_test
from .example_value_manager import ExampleValueManager, PreCommitHook
from .realtime_monitor import RealtimeMonitor, get_monitor, start_monitoring
from .smart_test_generator import SmartTestGenerator

__version__ = "1.0.0"

__all__ = [
    # 环境一致性
    "EnvironmentConsistencyManager",
    # 自适应架构
    "CapabilityRegistry",
    "adaptive_function",
    "AdaptiveQueryBuilder",
    "EnvironmentAwareService",
    "capability_registry",
    # 示例值管理
    "ExampleValueManager",
    "PreCommitHook",
    # 增强的Pre-commit
    "EnhancedPreCommitSystem",
    # 智能测试生成
    "SmartTestGenerator",
    # 环境模拟
    "EnvironmentSimulator",
    "cross_environment_test",
    # 实时监控
    "RealtimeMonitor",
    "get_monitor",
    "start_monitoring",
]


def setup_prevention_system(config: dict = None):
    """设置完整的预防系统"""
    if config is None:
        config = {}

    # 启动实时监控
    if config.get("enable_monitoring", True):
        start_monitoring()
        print("✅ Real-time monitoring started")

    # 设置环境一致性检查
    if config.get("enable_env_consistency", True):
        env_manager = EnvironmentConsistencyManager()
        print("✅ Environment consistency manager initialized")

    # 设置示例值管理
    if config.get("enable_example_management", True):
        example_manager = ExampleValueManager()
        print("✅ Example value manager initialized")

    # 设置增强的Pre-commit系统
    if config.get("enable_enhanced_precommit", True):
        precommit_system = EnhancedPreCommitSystem()
        print("✅ Enhanced pre-commit system initialized")

    print("🛡️ Prevention system setup complete!")

    return {
        "monitor": get_monitor() if config.get("enable_monitoring", True) else None,
        "env_manager": env_manager if config.get("enable_env_consistency", True) else None,
        "example_manager": example_manager if config.get("enable_example_management", True) else None,
        "precommit_system": precommit_system if config.get("enable_enhanced_precommit", True) else None,
    }


def quick_health_check():
    """快速健康检查"""
    print("🔍 Running quick health check...")

    # 检查示例值
    example_manager = ExampleValueManager()
    scan_results = example_manager.validate_examples(".")

    if scan_results["total_issues"] > 0:
        print(f"⚠️  Found {scan_results['total_issues']} example value issues")
        high_risk = scan_results["issues_by_risk"].get("high", 0)
        if high_risk > 0:
            print(f"🚨 {high_risk} high-risk issues found!")
    else:
        print("✅ No example value issues found")

    # 检查环境一致性
    try:
        from app.models import SessionLocal

        with SessionLocal() as db:
            env_manager = EnvironmentConsistencyManager()
            profile = env_manager.capture_environment_profile("current", db)
            print(f"✅ Environment profile captured: {profile.name}")
    except Exception as e:
        print(f"⚠️  Environment check failed: {e}")

    # 检查监控状态
    monitor = get_monitor()
    health_status = monitor.get_health_status()
    print(f"📊 System health: {health_status['status']}")

    return scan_results["total_issues"] == 0 and health_status["status"] != "critical"
