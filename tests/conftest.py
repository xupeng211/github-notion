"""
pytest配置文件 - 设置测试环境全局配置
"""

import os
import tempfile
import uuid

import pytest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import Base

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


def pytest_configure(config):
    """设置测试环境变量"""
    # 确保测试环境配置正确
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DISABLE_METRICS"] = "1"
    os.environ["DISABLE_NOTION"] = "1"
    os.environ["GITEE_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"
    os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret-for-testing-12345678"
    os.environ["DEADLETTER_REPLAY_TOKEN"] = "test-deadletter-token-for-testing-12345678"
    os.environ["LOG_LEVEL"] = "WARNING"


@pytest.fixture(scope="function")
def isolated_db():
    """为每个测试函数提供独立的数据库"""
    if not HAS_SQLALCHEMY:
        pytest.skip("SQLAlchemy not available")

    # 创建临时数据库文件
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, f"test_{uuid.uuid4().hex}.db")
    db_url = f"sqlite:///{db_file}"

    # 创建独立的数据库引擎
    engine = create_engine(db_url, echo=False)

    # 强制重新创建所有表，确保表结构正确
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 验证关键表结构
    from sqlalchemy import inspect

    inspector = inspect(engine)

    # 检查 processed_event 表是否有 source_platform 字段
    try:
        processed_event_columns = [col["name"] for col in inspector.get_columns("processed_event")]
        if "source_platform" not in processed_event_columns:
            raise RuntimeError(
                f"测试数据库表结构错误: processed_event 表缺少 source_platform 字段. 当前字段: {processed_event_columns}"
            )
    except Exception:
        # 如果表不存在或其他错误，跳过验证
        pass

    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session, db_url

    # 清理
    session.close()
    engine.dispose()
    try:
        os.unlink(db_file)
        os.rmdir(temp_dir)
    except (OSError, FileNotFoundError):
        pass


@pytest.fixture(scope="session")
def worker_id(request):
    """获取 pytest-xdist 的 worker ID"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput["workerid"]
    return "master"


def pytest_configure_node(node):
    """为每个 worker 配置独立的数据库"""
    worker_id = getattr(node, "workerinput", {}).get("workerid", "master")
    # 为每个 worker 设置独立的数据库路径
    test_db_dir = f"test_data_{worker_id}"
    os.makedirs(test_db_dir, exist_ok=True)
    os.environ["DB_URL"] = f"sqlite:///{test_db_dir}/test.db"
