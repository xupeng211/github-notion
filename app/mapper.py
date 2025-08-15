"""
增强的字段映射和数据转换模块

提供 GitHub 和 Notion 之间的双向数据映射功能，
支持复杂的字段转换、类型处理和智能映射规则。
"""
import logging
import yaml
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FieldMapper:
    """字段映射器类"""

    def __init__(self, config_path: str = "app/mapping.yml"):
        """初始化映射器

        Args:
            config_path: 映射配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载映射配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load mapping config from {self.config_path}: {e}")
            return {}

    def reload_config(self) -> bool:
        """重新加载配置"""
        try:
            self.config = self._load_config()
            logger.info("Mapping configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload mapping config: {e}")
            return False

    def github_to_notion(self, github_data: Dict[str, Any]) -> Dict[str, Any]:
        """将 GitHub Issue 数据转换为 Notion 页面属性

        Args:
            github_data: GitHub Issue 数据

        Returns:
            Notion 页面属性字典
        """
        properties = {}
        mappings = self.config.get('github_to_notion', {})
        field_types = self.config.get('field_types', {})
        status_mapping = self.config.get('status_mapping', {}).get('github_to_notion', {})

        for github_field, notion_field in mappings.items():
            value = self._get_nested_value(github_data, github_field)
            if value is None:
                continue

            # 获取字段类型
            field_type = field_types.get(notion_field, 'rich_text')

            # 特殊处理状态字段
            if github_field == 'state' and value in status_mapping:
                value = status_mapping[value]

            # 根据字段类型转换数据
            notion_value = self._convert_to_notion_type(value, field_type, github_field, github_data)

            if notion_value is not None:
                properties[notion_field] = notion_value

        return properties

    def notion_to_github(self, notion_page: Dict[str, Any]) -> Dict[str, Any]:
        """将 Notion 页面数据转换为 GitHub Issue 更新数据

        Args:
            notion_page: Notion 页面数据

        Returns:
            GitHub Issue 更新数据字典
        """
        github_data: Dict[str, Any] = {}
        mappings = self.config.get('notion_to_github', {})
        status_mapping = self.config.get('status_mapping', {}).get('notion_to_github', {})

        properties = notion_page.get('properties', {})

        for notion_field, github_field in mappings.items():
            notion_property = properties.get(notion_field)
            if not notion_property:
                continue

            value = self._extract_notion_value(notion_property)
            if value is None:
                continue

            # 特殊处理状态字段
            if notion_field == 'Status' and value in status_mapping:
                value = status_mapping[value]

            # 处理嵌套字段（如 labels.primary）
            if '.' in github_field:
                self._set_nested_value(github_data, github_field, value)
            else:
                github_data[github_field] = value

        return github_data

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字段值

        Args:
            data: 数据字典
            path: 字段路径，支持点号分隔（如 'user.login'）和数组索引（如 'labels.0.name'）

        Returns:
            字段值或 None
        """
        try:
            current = data
            parts = path.split('.')

            for part in parts:
                if current is None:
                    return None

                # 处理数组索引
                if part.isdigit():
                    index = int(part)
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                else:
                    current = current.get(part) if isinstance(current, dict) else None

            return current
        except Exception as e:
            logger.debug(f"Failed to get nested value for path '{path}': {e}")
            return None

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套字段值"""
        try:
            parts = path.split('.')
            current = data

            # 导航到最后一级的父对象
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # 设置最终值
            current[parts[-1]] = value
        except Exception as e:
            logger.error(f"Failed to set nested value for path '{path}': {e}")

    def _convert_to_notion_type(self, value: Any, field_type: str,
                               github_field: str, full_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将值转换为 Notion 字段类型格式

        Args:
            value: 原始值
            field_type: Notion 字段类型
            github_field: GitHub 字段名（用于特殊处理）
            full_data: 完整的 GitHub 数据（用于上下文）

        Returns:
            Notion 字段格式的数据或 None
        """
        try:
            if value is None or (isinstance(value, str) and not value.strip()):
                return None

            if field_type == 'title':
                return {
                    "title": [{"text": {"content": str(value)[:2000]}}]  # Notion 标题长度限制
                }

            elif field_type == 'rich_text':
                return {
                    "rich_text": [{"text": {"content": str(value)[:2000]}}]
                }

            elif field_type == 'select':
                return {
                    "select": {"name": str(value)[:100]}  # Select 选项名称长度限制
                }

            elif field_type == 'number':
                try:
                    return {"number": float(value)}
                except (ValueError, TypeError):
                    return None

            elif field_type == 'checkbox':
                return {"checkbox": bool(value)}

            elif field_type == 'url':
                url_value = str(value)
                if url_value.startswith(('http://', 'https://')):
                    return {"url": url_value}
                return None

            elif field_type == 'date':
                # 尝试解析日期
                date_str = self._parse_github_date(value)
                if date_str:
                    return {
                        "date": {"start": date_str}
                    }
                return None

            else:
                # 默认作为富文本处理
                return {
                    "rich_text": [{"text": {"content": str(value)[:2000]}}]
                }

        except Exception as e:
            logger.error(f"Failed to convert value '{value}' to Notion type '{field_type}': {e}")
            return None

    def _extract_notion_value(self, notion_property: Dict[str, Any]) -> Any:
        """从 Notion 属性中提取值

        Args:
            notion_property: Notion 属性对象

        Returns:
            提取的值或 None
        """
        try:
            prop_type = notion_property.get('type')

            if prop_type == 'title':
                title_list = notion_property.get('title', [])
                return ''.join([item.get('plain_text', '') for item in title_list])

            elif prop_type == 'rich_text':
                text_list = notion_property.get('rich_text', [])
                return ''.join([item.get('plain_text', '') for item in text_list])

            elif prop_type == 'select':
                select_obj = notion_property.get('select')
                return select_obj.get('name') if select_obj else None

            elif prop_type == 'multi_select':
                multi_select_list = notion_property.get('multi_select', [])
                return [item.get('name') for item in multi_select_list]

            elif prop_type == 'number':
                return notion_property.get('number')

            elif prop_type == 'checkbox':
                return notion_property.get('checkbox')

            elif prop_type == 'url':
                return notion_property.get('url')

            elif prop_type == 'date':
                date_obj = notion_property.get('date')
                return date_obj.get('start') if date_obj else None

            else:
                logger.debug(f"Unsupported Notion property type: {prop_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract value from Notion property: {e}")
            return None

    def _parse_github_date(self, date_str: str) -> Optional[str]:
        """解析 GitHub 日期格式

        Args:
            date_str: GitHub 日期字符串

        Returns:
            ISO 格式日期字符串或 None
        """
        try:
            # GitHub 使用 ISO 8601 格式
            # 例如: "2023-10-15T10:30:45Z"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.date().isoformat()
        except Exception as e:
            logger.debug(f"Failed to parse GitHub date '{date_str}': {e}")
            return None

    def should_ignore_event(self, data: Dict[str, Any], source: str) -> Tuple[bool, str]:
        """检查是否应该忽略此事件

        Args:
            data: 事件数据
            source: 事件源（'github' 或 'notion'）

        Returns:
            Tuple[是否忽略, 忽略原因]
        """
        sync_config = self.config.get('sync_config', {})

        # 检查双向同步开关
        if not sync_config.get('bidirectional_sync', True):
            return True, "bidirectional_sync_disabled"

        # 检查机器人用户
        if sync_config.get('ignore_bots', True):
            user_info = data.get('user') or data.get('sender')
            if user_info and user_info.get('type') == 'Bot':
                return True, "bot_user"

        # 检查忽略标签
        ignore_labels = sync_config.get('ignore_labels', [])
        if ignore_labels:
            issue_labels = []
            if source == 'github':
                issue_labels = [label.get('name') for label in data.get('labels', [])]

            for ignore_label in ignore_labels:
                if ignore_label in issue_labels:
                    return True, f"ignored_label:{ignore_label}"

        return False, ""

    def get_sync_config(self) -> Dict[str, Any]:
        """获取同步配置"""
        return self.config.get('sync_config', {})


# 全局实例
field_mapper = FieldMapper()
