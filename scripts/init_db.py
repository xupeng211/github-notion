#!/usr/bin/env python3
"""
数据库初始化脚本

此脚本用于生产环境部署时初始化数据库，替代之前的 init_db() 函数调用。
现在统一使用 alembic 管理数据库迁移，确保版本一致性。

使用方法:
    python scripts/init_db.py

环境变量:
    DB_URL: 数据库连接字符串，默认 sqlite:///data/sync.db
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from alembic import command
from alembic.config import Config


def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 确保数据目录存在
    db_url = os.getenv("DB_URL", "sqlite:///data/sync.db")
    if db_url.startswith("sqlite:///"):
        db_path = db_url[10:]  # 移除 "sqlite:///" 前缀
        data_dir = Path(db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 数据目录已创建: {data_dir}")
    
    # 设置 alembic 配置
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    
    print(f"✓ 数据库连接: {db_url}")
    
    # 运行迁移
    try:
        command.upgrade(alembic_cfg, "head")
        print("✓ 数据库迁移完成")
    except Exception as e:
        print(f"✗ 数据库迁移失败: {e}")
        return False
    
    print("✓ 数据库初始化完成")
    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1) 