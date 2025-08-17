"""
智能测试生成器
自动生成环境兼容性测试和边界条件测试
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TestCase:
    """测试用例定义"""

    name: str
    description: str
    test_code: str
    dependencies: List[str]
    environment_requirements: Dict[str, Any]


class SmartTestGenerator:
    """智能测试生成器"""

    def __init__(self):
        self.test_templates = self._load_test_templates()
        self.environment_scenarios = self._load_environment_scenarios()

    def _load_test_templates(self) -> Dict[str, str]:
        """加载测试模板"""
        return {
            "database_compatibility": '''
def test_{function_name}_database_compatibility(self, db_session):
    """测试{function_name}的数据库兼容性"""
    # 测试有source_platform字段的情况
    with patch('app.models._has_source_platform_column', return_value=True):
        result1 = {function_call}
        assert result1 is not None

    # 测试没有source_platform字段的情况
    with patch('app.models._has_source_platform_column', return_value=False):
        result2 = {function_call}
        assert result2 is not None

    # 结果应该一致（或有预期的差异）
    # assert result1 == result2  # 根据具体情况调整
''',
            "environment_adaptation": '''
def test_{function_name}_environment_adaptation(self, db_session):
    """测试{function_name}的环境适应性"""
    # 模拟不同环境能力
    test_scenarios = [
        {{"has_redis": True, "has_source_platform": True}},
        {{"has_redis": False, "has_source_platform": True}},
        {{"has_redis": True, "has_source_platform": False}},
        {{"has_redis": False, "has_source_platform": False}},
    ]

    for scenario in test_scenarios:
        with patch.multiple(
            'app.models',
            _has_source_platform_column=lambda db: scenario["has_source_platform"],
            # 添加其他能力检测的mock
        ):
            try:
                result = {function_call}
                # 验证在不同环境下都能正常工作
                assert result is not None
            except Exception as e:
                pytest.fail(f"Function failed in scenario {{scenario}}: {{e}}")
''',
            "webhook_payload_validation": '''
def test_{function_name}_webhook_payload_validation(self, db_session):
    """测试{function_name}的webhook payload验证"""
    # 完整payload测试
    complete_payload = {{
        "action": "opened",
        "issue": {{
            "id": 123,
            "number": 1,
            "title": "Test Issue",
            "body": "Test Description",
            "state": "open",
            "html_url": "https://example.com/issues/1",
            "user": {{"login": "testuser", "name": "Test User"}},
            "labels": []
        }},
        "repository": {{
            "id": 456,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "html_url": "https://example.com/testuser/test-repo",
            "owner": {{"login": "testuser", "name": "Test User"}}
        }},
        "sender": {{"login": "testuser", "name": "Test User"}}
    }}

    result = {function_call}
    assert result is not None

    # 测试缺少必需字段的情况
    incomplete_payloads = [
        # 缺少sender
        {{k: v for k, v in complete_payload.items() if k != "sender"}},
        # 缺少repository.owner
        {{**complete_payload, "repository": {{k: v for k, v in complete_payload["repository"].items() if k != "owner"}}}},
        # 缺少issue.html_url
        {{**complete_payload, "issue": {{k: v for k, v in complete_payload["issue"].items() if k != "html_url"}}}},
    ]

    for incomplete_payload in incomplete_payloads:
        with pytest.raises((ValueError, KeyError, ValidationError)):
            {function_call_with_incomplete_payload}
''',
            "error_handling": '''
def test_{function_name}_error_handling(self, db_session):
    """测试{function_name}的错误处理"""
    # 测试数据库连接错误
    with patch.object(db_session, 'query', side_effect=SQLAlchemyError("Database error")):
        with pytest.raises((SQLAlchemyError, RuntimeError)):
            {function_call}

    # 测试无效参数
    invalid_params = [
        None,
        "",
        "invalid_id",
        -1,
        {{"invalid": "data"}}
    ]

    for invalid_param in invalid_params:
        with pytest.raises((ValueError, TypeError, ValidationError)):
            {function_call_with_invalid_param}
''',
            "performance_boundary": '''
def test_{function_name}_performance_boundary(self, db_session):
    """测试{function_name}的性能边界"""
    import time

    # 测试大量数据处理
    large_data_sizes = [100, 1000, 5000]

    for size in large_data_sizes:
        start_time = time.time()

        # 生成测试数据
        test_data = [self._generate_test_data(i) for i in range(size)]

        # 执行函数
        results = []
        for data in test_data:
            result = {function_call_with_data}
            results.append(result)

        end_time = time.time()
        execution_time = end_time - start_time

        # 性能断言（根据实际需求调整）
        assert execution_time < size * 0.01  # 每个操作不超过10ms
        assert len(results) == size

        # 内存使用检查
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        assert memory_usage < 500  # 不超过500MB
''',
        }

    def _load_environment_scenarios(self) -> List[Dict[str, Any]]:
        """加载环境场景"""
        return [
            {
                "name": "local_development",
                "description": "本地开发环境",
                "capabilities": {
                    "has_source_platform_column": True,
                    "has_alembic_version": True,
                    "has_redis": True,
                    "has_notion": True,
                },
                "environment_vars": {"DISABLE_NOTION": "0", "LOG_LEVEL": "DEBUG"},
            },
            {
                "name": "ci_environment",
                "description": "CI测试环境",
                "capabilities": {
                    "has_source_platform_column": False,  # 新建数据库
                    "has_alembic_version": False,
                    "has_redis": False,
                    "has_notion": False,
                },
                "environment_vars": {"DISABLE_NOTION": "1", "LOG_LEVEL": "INFO"},
            },
            {
                "name": "production_environment",
                "description": "生产环境",
                "capabilities": {
                    "has_source_platform_column": True,
                    "has_alembic_version": True,
                    "has_redis": True,
                    "has_notion": True,
                },
                "environment_vars": {"DISABLE_NOTION": "0", "LOG_LEVEL": "WARNING"},
            },
            {
                "name": "minimal_environment",
                "description": "最小化环境",
                "capabilities": {
                    "has_source_platform_column": False,
                    "has_alembic_version": False,
                    "has_redis": False,
                    "has_notion": False,
                },
                "environment_vars": {"DISABLE_NOTION": "1", "LOG_LEVEL": "ERROR"},
            },
        ]

    def analyze_function(self, function_path: str, function_name: str) -> Dict[str, Any]:
        """分析函数特征"""
        try:
            with open(function_path, "r") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            return {"error": f"Failed to parse {function_path}: {e}"}

        function_info = {
            "name": function_name,
            "parameters": [],
            "return_type": None,
            "uses_database": False,
            "uses_external_api": False,
            "has_error_handling": False,
            "complexity_score": 0,
        }

        # 查找函数定义
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # 分析参数
                for arg in node.args.args:
                    function_info["parameters"].append(arg.arg)

                # 分析函数体
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Call):
                        # 检查数据库使用
                        if hasattr(stmt.func, "attr") and stmt.func.attr in ["query", "add", "commit", "rollback"]:
                            function_info["uses_database"] = True

                        # 检查外部API调用
                        if hasattr(stmt.func, "attr") and stmt.func.attr in ["get", "post", "put", "delete"]:
                            function_info["uses_external_api"] = True

                    # 检查错误处理
                    if isinstance(stmt, ast.ExceptHandler):
                        function_info["has_error_handling"] = True

                    # 计算复杂度
                    if isinstance(stmt, (ast.If, ast.For, ast.While, ast.Try)):
                        function_info["complexity_score"] += 1

                break

        return function_info

    def generate_tests_for_function(self, function_path: str, function_name: str) -> List[TestCase]:
        """为函数生成测试用例"""
        function_info = self.analyze_function(function_path, function_name)

        if "error" in function_info:
            return []

        test_cases = []

        # 基于函数特征选择测试模板
        if function_info["uses_database"]:
            test_cases.append(self._generate_database_compatibility_test(function_info))
            test_cases.append(self._generate_environment_adaptation_test(function_info))

        if "webhook" in function_name.lower() or "payload" in function_name.lower():
            test_cases.append(self._generate_webhook_validation_test(function_info))

        if not function_info["has_error_handling"] or function_info["complexity_score"] > 3:
            test_cases.append(self._generate_error_handling_test(function_info))

        if function_info["uses_external_api"] or function_info["complexity_score"] > 5:
            test_cases.append(self._generate_performance_test(function_info))

        return test_cases

    def _generate_database_compatibility_test(self, function_info: Dict[str, Any]) -> TestCase:
        """生成数据库兼容性测试"""
        function_name = function_info["name"]

        # 构造函数调用
        params = function_info["parameters"]
        if "db" in params or "session" in params:
            params = [p for p in params if p not in ["db", "session"]]

        param_values = []
        for param in params:
            if "id" in param:
                param_values.append('"test_id"')
            elif "hash" in param:
                param_values.append('"test_hash"')
            elif "platform" in param:
                param_values.append('"test_platform"')
            else:
                param_values.append('"test_value"')

        function_call = f"{function_name}(db_session, {', '.join(param_values)})"

        test_code = self.test_templates["database_compatibility"].format(
            function_name=function_name, function_call=function_call
        )

        return TestCase(
            name=f"test_{function_name}_database_compatibility",
            description=f"测试{function_name}的数据库兼容性",
            test_code=test_code,
            dependencies=["unittest.mock.patch"],
            environment_requirements={"database": "required"},
        )

    def _generate_environment_adaptation_test(self, function_info: Dict[str, Any]) -> TestCase:
        """生成环境适应性测试"""
        function_name = function_info["name"]

        # 构造函数调用（简化版）
        function_call = f"{function_name}(db_session, 'test_param')"

        test_code = self.test_templates["environment_adaptation"].format(
            function_name=function_name, function_call=function_call
        )

        return TestCase(
            name=f"test_{function_name}_environment_adaptation",
            description=f"测试{function_name}的环境适应性",
            test_code=test_code,
            dependencies=["unittest.mock.patch"],
            environment_requirements={"database": "required"},
        )

    def _generate_webhook_validation_test(self, function_info: Dict[str, Any]) -> TestCase:
        """生成webhook验证测试"""
        function_name = function_info["name"]

        function_call = f"{function_name}(complete_payload)"
        function_call_incomplete = f"{function_name}(incomplete_payload)"

        test_code = self.test_templates["webhook_payload_validation"].format(
            function_name=function_name,
            function_call=function_call,
            function_call_with_incomplete_payload=function_call_incomplete,
        )

        return TestCase(
            name=f"test_{function_name}_webhook_payload_validation",
            description=f"测试{function_name}的webhook payload验证",
            test_code=test_code,
            dependencies=["pytest"],
            environment_requirements={},
        )

    def _generate_error_handling_test(self, function_info: Dict[str, Any]) -> TestCase:
        """生成错误处理测试"""
        function_name = function_info["name"]

        function_call = f"{function_name}(db_session, 'valid_param')"
        function_call_invalid = f"{function_name}(db_session, invalid_param)"

        test_code = self.test_templates["error_handling"].format(
            function_name=function_name,
            function_call=function_call,
            function_call_with_invalid_param=function_call_invalid,
        )

        return TestCase(
            name=f"test_{function_name}_error_handling",
            description=f"测试{function_name}的错误处理",
            test_code=test_code,
            dependencies=["pytest", "unittest.mock.patch", "sqlalchemy.exc.SQLAlchemyError"],
            environment_requirements={"database": "required"},
        )

    def _generate_performance_test(self, function_info: Dict[str, Any]) -> TestCase:
        """生成性能测试"""
        function_name = function_info["name"]

        function_call = f"{function_name}(db_session, data)"

        test_code = self.test_templates["performance_boundary"].format(
            function_name=function_name, function_call_with_data=function_call
        )

        return TestCase(
            name=f"test_{function_name}_performance_boundary",
            description=f"测试{function_name}的性能边界",
            test_code=test_code,
            dependencies=["time", "psutil"],
            environment_requirements={"database": "required"},
        )

    def generate_test_file(self, source_file: str, output_file: str = None) -> str:
        """为源文件生成完整的测试文件"""
        if output_file is None:
            source_path = Path(source_file)
            output_file = f"tests/test_{source_path.stem}.py"

        # 分析源文件中的所有函数
        try:
            with open(source_file, "r") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            return f"Error parsing {source_file}: {e}"

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                functions.append(node.name)

        # 为每个函数生成测试
        all_test_cases = []
        for func_name in functions:
            test_cases = self.generate_tests_for_function(source_file, func_name)
            all_test_cases.extend(test_cases)

        # 生成测试文件内容
        test_file_content = self._generate_test_file_content(all_test_cases, source_file)

        # 写入文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            f.write(test_file_content)

        return output_file

    def _generate_test_file_content(self, test_cases: List[TestCase], source_file: str) -> str:
        """生成测试文件内容"""
        lines = []

        # 文件头部
        lines.append('"""')
        lines.append(f"Auto-generated tests for {source_file}")
        lines.append("Generated by SmartTestGenerator")
        lines.append('"""')
        lines.append("")

        # 导入语句
        imports = set()
        imports.add("import pytest")
        imports.add("from unittest.mock import patch, MagicMock")
        imports.add("from sqlalchemy.exc import SQLAlchemyError")

        for test_case in test_cases:
            for dep in test_case.dependencies:
                if "." in dep:
                    imports.add(f'from {dep.rsplit(".", 1)[0]} import {dep.rsplit(".", 1)[1]}')
                else:
                    imports.add(f"import {dep}")

        for imp in sorted(imports):
            lines.append(imp)

        lines.append("")
        lines.append("# Import the module under test")
        module_name = Path(source_file).stem
        lines.append(f"from app import {module_name}")
        lines.append("")

        # 测试类
        lines.append(f"class Test{module_name.title()}:")
        lines.append('    """Auto-generated test class"""')
        lines.append("")

        # 测试用例
        for test_case in test_cases:
            lines.append("    " + test_case.test_code.replace("\n", "\n    "))
            lines.append("")

        return "\n".join(lines)


def main():
    """命令行工具"""
    import argparse

    parser = argparse.ArgumentParser(description="Smart Test Generator")
    parser.add_argument("source_file", help="Source file to generate tests for")
    parser.add_argument("--output", "-o", help="Output test file")
    parser.add_argument("--function", "-f", help="Specific function to test")

    args = parser.parse_args()

    generator = SmartTestGenerator()

    if args.function:
        test_cases = generator.generate_tests_for_function(args.source_file, args.function)
        for test_case in test_cases:
            print(f"# {test_case.name}")
            print(test_case.test_code)
            print()
    else:
        output_file = generator.generate_test_file(args.source_file, args.output)
        print(f"Generated test file: {output_file}")


if __name__ == "__main__":
    main()
