"""
测试数据模型 - 提高覆盖率
"""

from datetime import datetime, timezone

from app.models import Mapping, SyncEvent, init_db


class TestModels:
    """测试数据模型"""

    def test_sync_event_creation(self, isolated_db):
        """测试 SyncEvent 模型创建"""
        session, _ = isolated_db

        event = SyncEvent(
            event_id="test-event-123",
            source_platform="github",
            event_type="issues",
            payload={"action": "opened", "issue": {"id": 123}},
            status="pending",
        )

        session.add(event)
        session.commit()

        # 验证创建成功
        retrieved = session.query(SyncEvent).filter_by(event_id="test-event-123").first()
        assert retrieved is not None
        assert retrieved.source_platform == "github"
        assert retrieved.event_type == "issues"
        assert retrieved.status == "pending"
        assert retrieved.created_at is not None

    def test_mapping_creation(self, isolated_db):
        """测试 Mapping 模型创建"""
        session, _ = isolated_db

        mapping = Mapping(
            source_platform="github",
            source_id="123",
            source_url="https://github.com/user/repo/issues/123",
            notion_page_id="page-123",
            notion_database_id="db-123",
            sync_enabled=True,
        )

        session.add(mapping)
        session.commit()

        # 验证创建成功
        retrieved = session.query(Mapping).filter_by(source_id="123").first()
        assert retrieved is not None
        assert retrieved.source_platform == "github"
        assert retrieved.notion_page_id == "page-123"
        assert retrieved.sync_enabled is True

    def test_sync_event_status_update(self, isolated_db):
        """测试 SyncEvent 状态更新"""
        session, _ = isolated_db

        event = SyncEvent(
            event_id="test-event-456",
            source_platform="gitee",
            event_type="pull_request",
            payload={"action": "opened"},
            status="pending",
        )

        session.add(event)
        session.commit()

        # 更新状态
        event.status = "completed"
        event.processed_at = datetime.now(timezone.utc)
        session.commit()

        # 验证更新成功
        retrieved = session.query(SyncEvent).filter_by(event_id="test-event-456").first()
        assert retrieved.status == "completed"
        assert retrieved.processed_at is not None

    def test_mapping_sync_hash_update(self, isolated_db):
        """测试 Mapping 同步哈希更新"""
        session, _ = isolated_db

        mapping = Mapping(source_platform="gitee", source_id="456", notion_page_id="page-456", sync_enabled=True)

        session.add(mapping)
        session.commit()

        # 更新同步信息
        mapping.sync_hash = "abc123def456"
        mapping.last_sync_at = datetime.now(timezone.utc)
        session.commit()

        # 验证更新成功
        retrieved = session.query(Mapping).filter_by(source_id="456").first()
        assert retrieved.sync_hash == "abc123def456"
        assert retrieved.last_sync_at is not None

    def test_init_db_function(self, tmp_path):
        """测试 init_db 函数"""
        import os

        # 临时改变工作目录
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # 测试 init_db 函数
            init_db()

            # 验证 data 目录被创建
            assert os.path.exists("data")

        finally:
            os.chdir(original_cwd)

    def test_model_relationships(self, isolated_db):
        """测试模型关系和约束"""
        session, _ = isolated_db

        # 创建多个相关记录
        event1 = SyncEvent(
            event_id="event-1",
            source_platform="github",
            event_type="issues",
            payload={"issue_id": 1},
            status="completed",
        )

        event2 = SyncEvent(
            event_id="event-2", source_platform="github", event_type="issues", payload={"issue_id": 1}, status="pending"
        )

        mapping = Mapping(source_platform="github", source_id="1", notion_page_id="page-1", sync_enabled=True)

        session.add_all([event1, event2, mapping])
        session.commit()

        # 验证查询
        github_events = session.query(SyncEvent).filter_by(source_platform="github").all()
        assert len(github_events) == 2

        completed_events = session.query(SyncEvent).filter_by(status="completed").all()
        assert len(completed_events) == 1

        github_mappings = session.query(Mapping).filter_by(source_platform="github").all()
        assert len(github_mappings) == 1
