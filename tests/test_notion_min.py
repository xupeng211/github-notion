"""
最小化notion.py覆盖率测试
专注于最便宜的覆盖点：初始化、兼容性类
"""

from unittest.mock import patch


class TestNotionMinimal:
    """notion.py最小覆盖率测试"""

    def test_notion_service_init_with_env(self):
        """测试Notion服务初始化 - 有环境变量"""
        with patch.dict("os.environ", {"NOTION_TOKEN": "secret_test_token", "NOTION_DATABASE_ID": "test_database_id"}):
            from app.notion import NotionService

            service = NotionService()
            assert service.token == "secret_test_token"
            assert service.database_id == "test_database_id"

    def test_notion_service_init_without_env(self):
        """测试Notion服务初始化 - 无环境变量"""
        with patch.dict("os.environ", {}, clear=True):
            from app.notion import NotionService

            service = NotionService()
            assert service.token == ""
            assert service.database_id == ""

    def test_notion_service_init_with_params(self):
        """测试Notion服务初始化 - 使用参数"""
        from app.notion import NotionService

        service = NotionService(token="param_token", database_id="param_db_id")
        assert service.token == "param_token"
        assert service.database_id == "param_db_id"

    def test_notion_service_init_mixed_params(self):
        """测试Notion服务初始化 - 混合参数和环境变量"""
        with patch.dict("os.environ", {"NOTION_TOKEN": "env_token", "NOTION_DATABASE_ID": "env_db_id"}):
            from app.notion import NotionService

            # 参数优先于环境变量
            service = NotionService(token="param_token")
            assert service.token == "param_token"
            assert service.database_id == "env_db_id"  # 从环境变量获取

    def test_notion_client_compatibility_init(self):
        """测试NotionClient兼容性类初始化"""
        from app.notion import NotionClient

        client = NotionClient(token="compat_token")
        assert client.token == "compat_token"
        # NotionClient继承自NotionService，应该有相同的属性
        assert hasattr(client, "database_id")

    def test_notion_client_inheritance(self):
        """测试NotionClient继承关系"""
        from app.notion import NotionClient, NotionService

        client = NotionClient(token="test_token")
        assert isinstance(client, NotionService)
        assert isinstance(client, NotionClient)

    def test_notion_service_global_instance(self):
        """测试Notion服务全局实例"""
        from app.notion import notion_service

        # 验证全局实例存在
        assert notion_service is not None
        assert hasattr(notion_service, "token")
        assert hasattr(notion_service, "database_id")

    def test_notion_service_attributes(self):
        """测试Notion服务属性设置"""
        from app.notion import NotionService

        # 测试默认属性
        service = NotionService()
        assert hasattr(service, "token")
        assert hasattr(service, "database_id")

        # 测试属性类型
        assert isinstance(service.token, str)
        assert isinstance(service.database_id, str)
