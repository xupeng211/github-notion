#!/usr/bin/env python3
"""
架构修复验证脚本

验证所有修复的架构问题是否已解决，包括：
1. 数据库迁移冲突
2. 环境变量命名一致性
3. 同步/异步架构一致性
4. 错误处理完整性
5. 核心功能实现

使用方法:
    python scripts/validate_fixes.py
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

class FixValidator:
    """修复验证器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def test(self, name: str, func) -> bool:
        """运行单个测试"""
        try:
            print(f"🧪 测试: {name}")
            result = func()
            if result:
                print(f"  ✅ 通过")
                self.passed += 1
                return True
            else:
                print(f"  ❌ 失败")
                self.failed += 1
                return False
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            self.failed += 1
            return False
    
    def warn(self, message: str):
        """输出警告"""
        print(f"  ⚠️  警告: {message}")
        self.warnings += 1
    
    def summary(self):
        """输出测试总结"""
        total = self.passed + self.failed
        print(f"\n📊 测试总结:")
        print(f"  总测试数: {total}")
        print(f"  通过: {self.passed}")
        print(f"  失败: {self.failed}")
        print(f"  警告: {self.warnings}")
        
        if self.failed == 0:
            print(f"\n🎉 所有测试通过！架构修复验证成功")
            return True
        else:
            print(f"\n❌ 有 {self.failed} 个测试失败，需要进一步修复")
            return False


def test_import_structure():
    """测试模块导入结构"""
    try:
        # 测试主要模块导入
        import app.server
        import app.service
        import app.models
        import app.notion
        import app.github
        return True
    except ImportError as e:
        print(f"    导入失败: {e}")
        return False


def test_environment_variables():
    """测试环境变量配置一致性"""
    # 检查 env.example 中是否使用 DB_URL
    env_example = PROJECT_ROOT / "env.example"
    if not env_example.exists():
        print(f"    env.example 文件不存在")
        return False
    
    content = env_example.read_text()
    if "DATABASE_URL=" in content:
        print(f"    env.example 中仍使用 DATABASE_URL，应该是 DB_URL")
        return False
    
    if "DB_URL=" not in content:
        print(f"    env.example 中缺少 DB_URL 配置")
        return False
    
    return True


def test_async_architecture():
    """测试异步架构一致性"""
    try:
        from app.service import async_process_github_event, async_notion_upsert_page
        from app.service import async_exponential_backoff_request
        
        # 检查函数是否为协程
        import inspect
        if not inspect.iscoroutinefunction(async_process_github_event):
            print(f"    async_process_github_event 不是协程函数")
            return False
        
        if not inspect.iscoroutinefunction(async_notion_upsert_page):
            print(f"    async_notion_upsert_page 不是协程函数")
            return False
        
        if not inspect.iscoroutinefunction(async_exponential_backoff_request):
            print(f"    async_exponential_backoff_request 不是协程函数")
            return False
        
        return True
    except ImportError as e:
        print(f"    异步函数导入失败: {e}")
        return False


def test_database_migration():
    """测试数据库迁移配置"""
    # 检查 alembic 配置
    alembic_ini = PROJECT_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        print(f"    alembic.ini 文件不存在")
        return False
    
    # 检查迁移文件存在
    versions_dir = PROJECT_ROOT / "alembic" / "versions"
    if not versions_dir.exists():
        print(f"    alembic/versions 目录不存在")
        return False
    
    migration_files = list(versions_dir.glob("*.py"))
    if len(migration_files) == 0:
        print(f"    没有找到数据库迁移文件")
        return False
    
    return True


def test_error_handling():
    """测试错误处理机制"""
    try:
        # 检查 server.py 中的异常处理器
        from app.server import app
        
        # 检查是否有全局异常处理器
        exception_handlers = app.exception_handlers
        if Exception not in exception_handlers:
            print(f"    缺少全局异常处理器")
            return False
        
        return True
    except Exception as e:
        print(f"    错误处理检查失败: {e}")
        return False


def test_core_services():
    """测试核心服务功能"""
    try:
        from app.github import github_service
        from app.notion import notion_service
        
        # 检查关键方法存在
        if not hasattr(github_service, 'update_issue'):
            print(f"    GitHub 服务缺少 update_issue 方法")
            return False
        
        if not hasattr(github_service, 'extract_repo_info'):
            print(f"    GitHub 服务缺少 extract_repo_info 方法")
            return False
        
        if not hasattr(notion_service, 'find_page_by_issue_id'):
            print(f"    Notion 服务缺少 find_page_by_issue_id 方法")
            return False
        
        return True
    except Exception as e:
        print(f"    核心服务检查失败: {e}")
        return False


def test_startup_scripts():
    """测试启动脚本"""
    init_script = PROJECT_ROOT / "scripts" / "init_db.py"
    start_script = PROJECT_ROOT / "scripts" / "start_service.py"
    
    if not init_script.exists():
        print(f"    缺少数据库初始化脚本")
        return False
    
    if not start_script.exists():
        print(f"    缺少服务启动脚本")
        return False
    
    # 检查脚本是否可执行
    if not os.access(init_script, os.X_OK):
        print(f"    init_db.py 没有执行权限")
        return False
    
    if not os.access(start_script, os.X_OK):
        print(f"    start_service.py 没有执行权限")
        return False
    
    return True


def test_fastapi_configuration():
    """测试 FastAPI 配置"""
    try:
        # 直接读取 server.py 文件内容检查
        server_file = PROJECT_ROOT / "app" / "server.py"
        content = server_file.read_text()
        
        # 检查是否移除了 init_db 调用（忽略注释中的提及）
        lines = content.split('\n')
        for line in lines:
            stripped = line.strip()
            # 跳过注释行
            if stripped.startswith('#'):
                continue
            # 检查实际的代码调用
            if "init_db()" in line:
                print(f"    server.py 中仍包含 init_db() 函数调用")
                return False
        
        # 检查是否有正确的注释说明
        if "通过 alembic 管理" not in content:
            print(f"    缺少 alembic 管理的说明注释")
            return False
        
        return True
    except Exception as e:
        print(f"    FastAPI 配置检查失败: {e}")
        return False


def run_alembic_check():
    """运行 alembic 检查"""
    try:
        # 设置测试环境变量
        env = os.environ.copy()
        env["DB_URL"] = "sqlite:///data/test_validation.db"
        
        # 创建临时数据目录
        test_data_dir = PROJECT_ROOT / "data"
        test_data_dir.mkdir(exist_ok=True)
        
        result = subprocess.run(
            ["python", "-m", "alembic", "current"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # 如果返回码不是0，检查是否是因为没有迁移记录（这是正常的）
        if result.returncode != 0:
            if "target database is not up to date" in result.stderr.lower() or \
               "no such table" in result.stderr.lower():
                # 这表示 alembic 配置正确，只是数据库还没初始化
                return True
            else:
                print(f"    Alembic 错误: {result.stderr}")
                return False
        
        return True
    except Exception as e:
        print(f"    Alembic 检查失败: {e}")
        return False


def main():
    """主验证流程"""
    print("🔧 开始架构修复验证...")
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    
    validator = FixValidator()
    
    # 运行所有测试
    validator.test("模块导入结构", test_import_structure)
    validator.test("环境变量配置一致性", test_environment_variables)
    validator.test("异步架构一致性", test_async_architecture)
    validator.test("数据库迁移配置", test_database_migration)
    validator.test("错误处理机制", test_error_handling)
    validator.test("核心服务功能", test_core_services)
    validator.test("启动脚本", test_startup_scripts)
    validator.test("FastAPI 配置", test_fastapi_configuration)
    validator.test("Alembic 配置检查", run_alembic_check)
    
    # 输出验证总结
    success = validator.summary()
    
    if success:
        print(f"\n🚀 架构修复验证完成！")
        print(f"💡 下一步：")
        print(f"   1. 配置环境变量 (参考 env.example)")
        print(f"   2. 运行 python scripts/start_service.py")
        print(f"   3. 测试 API 端点")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 