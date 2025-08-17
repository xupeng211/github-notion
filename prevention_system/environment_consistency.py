"""
环境一致性保障系统
确保本地、CI、生产环境的行为一致性
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from sqlalchemy import inspect
from sqlalchemy.orm import Session


@dataclass
class EnvironmentProfile:
    """环境配置档案"""

    name: str
    python_version: str
    dependencies: Dict[str, str]
    database_schema: Dict[str, Any]
    environment_variables: List[str]
    capabilities: Dict[str, bool]


class EnvironmentConsistencyManager:
    """环境一致性管理器"""

    def __init__(self):
        self.profiles: Dict[str, EnvironmentProfile] = {}

    def capture_environment_profile(self, name: str, db: Session) -> EnvironmentProfile:
        """捕获当前环境配置档案"""
        return EnvironmentProfile(
            name=name,
            python_version=self._get_python_version(),
            dependencies=self._get_dependencies(),
            database_schema=self._get_database_schema(db),
            environment_variables=self._get_required_env_vars(),
            capabilities=self._detect_capabilities(db),
        )

    def _get_python_version(self) -> str:
        """获取Python版本"""
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_dependencies(self) -> Dict[str, str]:
        """获取依赖版本"""
        try:
            import pkg_resources

            return {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
        except Exception:
            return {}

    def _get_database_schema(self, db: Session) -> Dict[str, Any]:
        """获取数据库模式信息"""
        inspector = inspect(db.bind)
        schema = {}

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema[table_name] = {
                "columns": [col["name"] for col in columns],
                "column_types": {col["name"]: str(col["type"]) for col in columns},
            }

        return schema

    def _get_required_env_vars(self) -> List[str]:
        """获取必需的环境变量"""
        required_vars = [
            "NOTION_TOKEN",
            "GITEE_WEBHOOK_SECRET",
            "GITHUB_WEBHOOK_SECRET",
            "DB_URL",
            "LOG_LEVEL",
            "APP_PORT",
        ]
        return [var for var in required_vars if os.getenv(var)]

    def _detect_capabilities(self, db: Session) -> Dict[str, bool]:
        """检测环境能力"""
        capabilities = {}

        # 检测数据库功能
        try:
            inspector = inspect(db.bind)
            processed_event_columns = []
            if "processed_event" in inspector.get_table_names():
                columns = inspector.get_columns("processed_event")
                processed_event_columns = [col["name"] for col in columns]

            capabilities["has_source_platform_column"] = "source_platform" in processed_event_columns
            capabilities["has_alembic_version"] = "alembic_version" in inspector.get_table_names()
        except Exception as e:
            capabilities["database_error"] = str(e)

        # 检测其他功能
        capabilities["has_redis"] = bool(os.getenv("REDIS_URL"))
        capabilities["has_notion"] = bool(os.getenv("NOTION_TOKEN"))

        return capabilities

    def compare_environments(self, profile1: str, profile2: str) -> Dict[str, Any]:
        """比较两个环境的差异"""
        if profile1 not in self.profiles or profile2 not in self.profiles:
            raise ValueError("Profile not found")

        p1, p2 = self.profiles[profile1], self.profiles[profile2]

        differences = {
            "python_version": p1.python_version != p2.python_version,
            "schema_differences": self._compare_schemas(p1.database_schema, p2.database_schema),
            "capability_differences": self._compare_capabilities(p1.capabilities, p2.capabilities),
            "missing_env_vars": set(p1.environment_variables) - set(p2.environment_variables),
        }

        return differences

    def _compare_schemas(self, schema1: Dict, schema2: Dict) -> Dict[str, Any]:
        """比较数据库模式差异"""
        differences = {}

        all_tables = set(schema1.keys()) | set(schema2.keys())

        for table in all_tables:
            if table not in schema1:
                differences[table] = {"status": "missing_in_env1"}
            elif table not in schema2:
                differences[table] = {"status": "missing_in_env2"}
            else:
                cols1 = set(schema1[table]["columns"])
                cols2 = set(schema2[table]["columns"])

                if cols1 != cols2:
                    differences[table] = {"missing_columns": list(cols1 - cols2), "extra_columns": list(cols2 - cols1)}

        return differences

    def _compare_capabilities(self, cap1: Dict, cap2: Dict) -> Dict[str, Any]:
        """比较环境能力差异"""
        differences = {}

        all_caps = set(cap1.keys()) | set(cap2.keys())

        for cap in all_caps:
            val1 = cap1.get(cap)
            val2 = cap2.get(cap)

            if val1 != val2:
                differences[cap] = {"env1": val1, "env2": val2}

        return differences

    def generate_compatibility_adapter(self, differences: Dict[str, Any]) -> str:
        """根据差异生成兼容性适配器代码"""
        adapter_code = []

        adapter_code.append("# Auto-generated compatibility adapter")
        adapter_code.append("from sqlalchemy import inspect")
        adapter_code.append("from sqlalchemy.orm import Session")
        adapter_code.append("")

        # 生成模式检测函数
        if differences.get("schema_differences"):
            for table, diff in differences["schema_differences"].items():
                if "missing_columns" in diff:
                    for col in diff["missing_columns"]:
                        adapter_code.append(f"def has_{table}_{col}_column(db: Session) -> bool:")
                        adapter_code.append(f"    inspector = inspect(db.bind)")
                        adapter_code.append(f"    if '{table}' not in inspector.get_table_names():")
                        adapter_code.append(f"        return False")
                        adapter_code.append(f"    columns = [col['name'] for col in inspector.get_columns('{table}')]")
                        adapter_code.append(f"    return '{col}' in columns")
                        adapter_code.append("")

        # 生成能力检测函数
        if differences.get("capability_differences"):
            for cap, diff in differences["capability_differences"].items():
                adapter_code.append(f"def check_{cap}(db: Session) -> bool:")
                adapter_code.append(f"    # Capability check for {cap}")
                adapter_code.append(f"    # Implement specific logic based on environment")
                adapter_code.append(f"    return True  # Placeholder")
                adapter_code.append("")

        return "\n".join(adapter_code)

    def save_profile(self, profile: EnvironmentProfile, filepath: str):
        """保存环境配置档案"""
        profile_data = {
            "name": profile.name,
            "python_version": profile.python_version,
            "dependencies": profile.dependencies,
            "database_schema": profile.database_schema,
            "environment_variables": profile.environment_variables,
            "capabilities": profile.capabilities,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(profile_data, f, indent=2)

    def load_profile(self, filepath: str) -> EnvironmentProfile:
        """加载环境配置档案"""
        with open(filepath, "r") as f:
            data = json.load(f)

        return EnvironmentProfile(
            name=data["name"],
            python_version=data["python_version"],
            dependencies=data["dependencies"],
            database_schema=data["database_schema"],
            environment_variables=data["environment_variables"],
            capabilities=data["capabilities"],
        )


# 使用示例
def setup_environment_monitoring():
    """设置环境监控"""
    manager = EnvironmentConsistencyManager()

    # 在不同环境中运行此代码来建立基线
    # 本地环境
    # local_profile = manager.capture_environment_profile("local", db_session)
    # manager.save_profile(local_profile, "profiles/local.json")

    # CI环境
    # ci_profile = manager.capture_environment_profile("ci", db_session)
    # manager.save_profile(ci_profile, "profiles/ci.json")

    # 比较环境差异
    # differences = manager.compare_environments("local", "ci")
    # adapter_code = manager.generate_compatibility_adapter(differences)

    return manager
