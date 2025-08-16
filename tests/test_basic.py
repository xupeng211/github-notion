"""
基础测试 - 验证基本功能和依赖
"""

import os
import sys

import pytest


def test_python_version():
    """测试 Python 版本"""
    assert sys.version_info >= (3, 11)


def test_environment_variables():
    """测试环境变量设置"""
    assert os.getenv("ENVIRONMENT") == "testing"
    assert os.getenv("DISABLE_METRICS") == "1"
    assert os.getenv("DISABLE_NOTION") == "1"


def test_sqlalchemy_import():
    """测试 SQLAlchemy 导入"""
    try:
        import sqlalchemy

        assert sqlalchemy.__version__ is not None
    except ImportError as e:
        pytest.fail(f"Failed to import SQLAlchemy: {e}")


def test_fastapi_import():
    """测试 FastAPI 导入"""
    try:
        import fastapi

        assert fastapi.__version__ is not None
    except ImportError as e:
        pytest.fail(f"Failed to import FastAPI: {e}")


def test_app_models_import():
    """测试应用模型导入"""
    try:
        from app.models import Base

        assert Base is not None
    except ImportError as e:
        pytest.fail(f"Failed to import app.models: {e}")


def test_basic_math():
    """基础数学测试 - 确保测试框架工作"""
    assert 1 + 1 == 2
    assert 2 * 3 == 6


def test_string_operations():
    """字符串操作测试"""
    test_str = "Hello, World!"
    assert len(test_str) == 13
    assert test_str.lower() == "hello, world!"
    assert "World" in test_str
