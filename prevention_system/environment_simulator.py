"""
环境模拟测试框架
模拟不同的运行环境进行测试
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, ContextManager, Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@dataclass
class EnvironmentConfig:
    """环境配置"""

    name: str
    description: str
    database_schema: Dict[str, Any]
    environment_variables: Dict[str, str]
    capabilities: Dict[str, bool]
    python_path: List[str]


class EnvironmentSimulator:
    """环境模拟器"""

    def __init__(self):
        self.environments = self._load_environment_configs()
        self.temp_dirs = []

    def _load_environment_configs(self) -> Dict[str, EnvironmentConfig]:
        """加载环境配置"""
        return {
            "local_dev": EnvironmentConfig(
                name="local_dev",
                description="本地开发环境",
                database_schema={
                    "processed_event": {
                        "columns": ["id", "issue_id", "content_hash", "source_platform", "created_at"],
                        "has_alembic": True,
                    },
                    "sync_event": {
                        "columns": ["id", "source_id", "entity_type", "action", "payload", "created_at"],
                        "has_alembic": True,
                    },
                },
                environment_variables={"DISABLE_NOTION": "0", "LOG_LEVEL": "DEBUG", "PYTHONPATH": "/app:/app/app"},
                capabilities={
                    "has_source_platform_column": True,
                    "has_alembic_version": True,
                    "has_redis": True,
                    "has_notion": True,
                },
                python_path=["/app", "/app/app"],
            ),
            "ci_fresh": EnvironmentConfig(
                name="ci_fresh",
                description="CI环境 - 全新数据库",
                database_schema={
                    "processed_event": {
                        "columns": ["id", "issue_id", "content_hash", "created_at"],  # 缺少source_platform
                        "has_alembic": False,
                    },
                    "sync_event": {
                        "columns": ["id", "source_id", "entity_type", "action", "payload", "created_at"],
                        "has_alembic": False,
                    },
                },
                environment_variables={
                    "DISABLE_NOTION": "1",
                    "LOG_LEVEL": "INFO",
                    "PYTHONPATH": "/github/workspace:/github/workspace/app",
                },
                capabilities={
                    "has_source_platform_column": False,
                    "has_alembic_version": False,
                    "has_redis": False,
                    "has_notion": False,
                },
                python_path=["/github/workspace", "/github/workspace/app"],
            ),
            "production": EnvironmentConfig(
                name="production",
                description="生产环境",
                database_schema={
                    "processed_event": {
                        "columns": ["id", "issue_id", "content_hash", "source_platform", "created_at"],
                        "has_alembic": True,
                    },
                    "sync_event": {
                        "columns": ["id", "source_id", "entity_type", "action", "payload", "created_at"],
                        "has_alembic": True,
                    },
                },
                environment_variables={
                    "DISABLE_NOTION": "0",
                    "LOG_LEVEL": "WARNING",
                    "PYTHONPATH": "/opt/app:/opt/app/app",
                },
                capabilities={
                    "has_source_platform_column": True,
                    "has_alembic_version": True,
                    "has_redis": True,
                    "has_notion": True,
                },
                python_path=["/opt/app", "/opt/app/app"],
            ),
            "minimal": EnvironmentConfig(
                name="minimal",
                description="最小化环境",
                database_schema={
                    "processed_event": {
                        "columns": ["id", "issue_id", "content_hash", "created_at"],
                        "has_alembic": False,
                    }
                },
                environment_variables={
                    "DISABLE_NOTION": "1",
                    "LOG_LEVEL": "ERROR",
                    "PYTHONPATH": "/minimal:/minimal/app",
                },
                capabilities={
                    "has_source_platform_column": False,
                    "has_alembic_version": False,
                    "has_redis": False,
                    "has_notion": False,
                },
                python_path=["/minimal", "/minimal/app"],
            ),
        }

    @contextmanager
    def simulate_environment(self, env_name: str) -> ContextManager[Dict[str, Any]]:
        """模拟指定环境"""
        if env_name not in self.environments:
            raise ValueError(f"Unknown environment: {env_name}")

        config = self.environments[env_name]

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix=f"env_sim_{env_name}_")
        self.temp_dirs.append(temp_dir)

        # 创建数据库
        db_path = os.path.join(temp_dir, "test.db")
        db_url = f"sqlite:///{db_path}"

        try:
            # 设置环境变量
            original_env = {}
            for key, value in config.environment_variables.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value

            # 设置数据库URL
            original_db_url = os.environ.get("DB_URL")
            os.environ["DB_URL"] = db_url

            # 创建数据库模式
            engine = create_engine(db_url)
            self._create_database_schema(engine, config.database_schema)

            # 创建会话
            SessionLocal = sessionmaker(bind=engine)

            # 模拟能力检测
            capability_mocks = self._create_capability_mocks(config.capabilities)

            yield {
                "config": config,
                "db_url": db_url,
                "engine": engine,
                "session_factory": SessionLocal,
                "temp_dir": temp_dir,
                "capability_mocks": capability_mocks,
            }

        finally:
            # 恢复环境变量
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

            if original_db_url is None:
                os.environ.pop("DB_URL", None)
            else:
                os.environ["DB_URL"] = original_db_url

            # 清理数据库连接
            engine.dispose()

    def _create_database_schema(self, engine, schema_config: Dict[str, Any]):
        """创建数据库模式"""
        with engine.connect() as conn:
            # 创建表
            for table_name, table_config in schema_config.items():
                columns = table_config["columns"]

                if table_name == "processed_event":
                    # 根据配置决定是否包含source_platform字段
                    if "source_platform" in columns:
                        create_sql = """
                        CREATE TABLE processed_event (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            issue_id VARCHAR(255) NOT NULL,
                            content_hash VARCHAR(255) NOT NULL,
                            source_platform VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    else:
                        create_sql = """
                        CREATE TABLE processed_event (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            issue_id VARCHAR(255) NOT NULL,
                            content_hash VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """

                elif table_name == "sync_event":
                    create_sql = """
                    CREATE TABLE sync_event (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_id VARCHAR(255) NOT NULL,
                        entity_type VARCHAR(50) NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        payload TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """

                else:
                    # 通用表创建逻辑
                    column_defs = []
                    for col in columns:
                        if col == "id":
                            column_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
                        elif "id" in col:
                            column_defs.append(f"{col} VARCHAR(255)")
                        elif "created_at" in col or "updated_at" in col:
                            column_defs.append(f"{col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                        else:
                            column_defs.append(f"{col} TEXT")

                    create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"

                conn.execute(text(create_sql))

            # 如果有alembic版本表，创建它
            for table_config in schema_config.values():
                if table_config.get("has_alembic", False):
                    try:
                        conn.execute(
                            text(
                                """
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL PRIMARY KEY
                        )
                        """
                            )
                        )
                        conn.execute(text("INSERT INTO alembic_version VALUES ('head')"))
                        break  # 只需要创建一次
                    except:
                        pass  # 表可能已存在

            conn.commit()

    def _create_capability_mocks(self, capabilities: Dict[str, bool]) -> Dict[str, Any]:
        """创建能力检测的模拟"""
        from unittest.mock import MagicMock

        mocks = {}

        # 模拟数据库字段检测
        def mock_has_source_platform_column(db):
            return capabilities.get("has_source_platform_column", False)

        def mock_has_alembic_version_table(db):
            return capabilities.get("has_alembic_version", False)

        mocks["has_source_platform_column"] = mock_has_source_platform_column
        mocks["has_alembic_version_table"] = mock_has_alembic_version_table

        # 模拟Redis连接
        if not capabilities.get("has_redis", False):
            redis_mock = MagicMock()
            redis_mock.ping.side_effect = Exception("Redis not available")
            mocks["redis"] = redis_mock

        # 模拟Notion API
        if not capabilities.get("has_notion", False):
            notion_mock = MagicMock()
            notion_mock.side_effect = Exception("Notion not available")
            mocks["notion"] = notion_mock

        return mocks

    def run_cross_environment_test(self, test_function, environments: List[str] = None) -> Dict[str, Any]:
        """在多个环境中运行测试"""
        if environments is None:
            environments = list(self.environments.keys())

        results = {}

        for env_name in environments:
            try:
                with self.simulate_environment(env_name) as env_context:
                    # 应用能力模拟
                    with self._apply_capability_mocks(env_context["capability_mocks"]):
                        # 运行测试
                        session = env_context["session_factory"]()
                        try:
                            result = test_function(session, env_context)
                            results[env_name] = {
                                "status": "success",
                                "result": result,
                                "environment": env_context["config"].description,
                            }
                        except Exception as e:
                            results[env_name] = {
                                "status": "error",
                                "error": str(e),
                                "environment": env_context["config"].description,
                            }
                        finally:
                            session.close()

            except Exception as e:
                results[env_name] = {
                    "status": "setup_error",
                    "error": str(e),
                    "environment": self.environments[env_name].description,
                }

        return results

    @contextmanager
    def _apply_capability_mocks(self, mocks: Dict[str, Any]):
        """应用能力模拟"""
        from unittest.mock import patch

        patches = []

        try:
            # 应用数据库能力模拟
            if "has_source_platform_column" in mocks:
                patch_obj = patch("app.models._has_source_platform_column", mocks["has_source_platform_column"])
                patches.append(patch_obj)
                patch_obj.start()

            if "has_alembic_version_table" in mocks:
                patch_obj = patch("app.models._has_alembic_version_table", mocks["has_alembic_version_table"])
                patches.append(patch_obj)
                patch_obj.start()

            # 应用Redis模拟
            if "redis" in mocks:
                patch_obj = patch("redis.from_url", return_value=mocks["redis"])
                patches.append(patch_obj)
                patch_obj.start()

            # 应用Notion模拟
            if "notion" in mocks:
                patch_obj = patch("requests.post", side_effect=mocks["notion"])
                patches.append(patch_obj)
                patch_obj.start()

            yield

        finally:
            # 停止所有补丁
            for patch_obj in patches:
                patch_obj.stop()

    def cleanup(self):
        """清理临时文件"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()

    def __del__(self):
        """析构函数"""
        self.cleanup()


# 测试装饰器
def cross_environment_test(environments: List[str] = None):
    """跨环境测试装饰器"""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            simulator = EnvironmentSimulator()

            def test_runner(session, env_context):
                # 将环境上下文传递给测试函数
                return test_func(session, env_context, *args, **kwargs)

            try:
                results = simulator.run_cross_environment_test(test_runner, environments)

                # 检查结果
                failed_envs = [env for env, result in results.items() if result["status"] != "success"]

                if failed_envs:
                    error_details = []
                    for env in failed_envs:
                        error_details.append(f"{env}: {results[env].get('error', 'Unknown error')}")

                    raise AssertionError(
                        f"Test failed in environments: {', '.join(failed_envs)}. Details: {'; '.join(error_details)}"
                    )

                return results

            finally:
                simulator.cleanup()

        return wrapper

    return decorator


# 使用示例
@cross_environment_test(["local_dev", "ci_fresh"])
def test_should_skip_event_cross_env(session, env_context):
    """跨环境测试should_skip_event函数"""
    from app.models import mark_event_processed, should_skip_event

    # 测试数据
    issue_id = "test_issue_123"
    platform = "gitee"
    content_hash = "test_hash_456"

    # 初始状态：应该不跳过
    should_skip = should_skip_event(session, issue_id, platform)
    assert not should_skip, f"Should not skip new event in {env_context['config'].name}"

    # 标记为已处理
    mark_event_processed(session, issue_id, content_hash, platform)

    # 再次检查：应该跳过
    should_skip = should_skip_event(session, issue_id, platform)
    assert should_skip, f"Should skip processed event in {env_context['config'].name}"

    return {"issue_id": issue_id, "platform": platform, "final_should_skip": should_skip}


def main():
    """命令行工具"""
    import argparse

    parser = argparse.ArgumentParser(description="Environment Simulator")
    parser.add_argument("command", choices=["list", "test", "simulate"])
    parser.add_argument("--environment", "-e", help="Environment name")
    parser.add_argument("--test-function", "-t", help="Test function to run")

    args = parser.parse_args()

    simulator = EnvironmentSimulator()

    if args.command == "list":
        print("Available environments:")
        for name, config in simulator.environments.items():
            print(f"  {name}: {config.description}")

    elif args.command == "simulate":
        if not args.environment:
            print("Error: --environment required for simulate command")
            return

        with simulator.simulate_environment(args.environment) as env_context:
            print(f"Simulating environment: {env_context['config'].description}")
            print(f"Database URL: {env_context['db_url']}")
            print(f"Temp directory: {env_context['temp_dir']}")
            print("Environment variables:")
            for key, value in env_context["config"].environment_variables.items():
                print(f"  {key}={value}")

            # 保持环境活跃，等待用户输入
            input("Press Enter to exit simulation...")

    elif args.command == "test":
        if args.test_function:
            # 运行指定的测试函数
            test_func = globals().get(args.test_function)
            if test_func:
                results = simulator.run_cross_environment_test(test_func)
                print("Test results:")
                for env, result in results.items():
                    print(f"  {env}: {result['status']}")
                    if result["status"] != "success":
                        print(f"    Error: {result.get('error', 'Unknown')}")
            else:
                print(f"Test function '{args.test_function}' not found")
        else:
            print("Error: --test-function required for test command")


if __name__ == "__main__":
    main()
