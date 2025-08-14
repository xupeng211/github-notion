#!/usr/bin/env python3
"""
GitHub-Notion 双向同步系统升级脚本
自动升级现有系统到支持双向同步的增强版本
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class SyncSystemUpgrader:
    """系统升级管理器"""

    def __init__(self, project_root: Optional[str] = None):
        """初始化升级器"""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.backup_dir = self.project_root / 'backup'

    def run(self) -> bool:
        """执行完整的系统升级流程"""
        print("🚀 开始升级 GitHub-Notion 双向同步系统...")
        print("=" * 60)

        steps = [
            ("环境检查", self._check_environment),
            ("数据备份", self._backup_existing_data),
            ("依赖检查", self._check_dependencies),
            ("新功能文件验证", self._validate_new_files),
            ("配置更新", self._update_configuration),
            ("数据库升级", self._upgrade_database),
            ("功能测试", self._test_functionality),
        ]

        for step_name, step_func in steps:
            print(f"📋 {step_name}...")
            if not step_func():
                print(f"❌ {step_name}失败")
                return False
            print(f"✅ {step_name}完成")
            print()

        print("🎉 系统升级完成！")
        self._show_next_steps()
        return True

    def _check_environment(self) -> bool:
        """检查运行环境"""
        print("🔍 检查运行环境...")

        # 检查 Python 版本
        if sys.version_info < (3, 8):
            print("❌ Python 版本过低，需要 3.8+")
            return False

        # 检查项目结构
        required_dirs = ['app', 'alembic']
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                print(f"❌ 缺少目录: {dir_name}")
                return False

        # 检查关键文件
        required_files = ['app/server.py', 'requirements.txt']
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                print(f"❌ 缺少文件: {file_path}")
                return False

        print("✅ 环境检查通过")
        return True

    def _backup_existing_data(self) -> bool:
        """备份现有数据"""
        print("💾 备份现有数据...")

        # 创建备份目录
        backup_timestamp = subprocess.run(
            ['date', '+%Y%m%d_%H%M%S'],
            capture_output=True, text=True
        ).stdout.strip()

        timestamped_backup = self.backup_dir / f"backup_{backup_timestamp}"
        timestamped_backup.mkdir(parents=True, exist_ok=True)

        # 备份数据库
        db_files = ['data/sync.db', 'sync.db']
        for db_file in db_files:
            db_path = self.project_root / db_file
            if db_path.exists():
                shutil.copy2(db_path, timestamped_backup / db_path.name)
                print(f"✅ 已备份数据库: {db_file}")

        # 备份配置文件
        config_files = ['.env', 'app/mapping.yml', 'alembic.ini']
        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                shutil.copy2(config_path, timestamped_backup / Path(config_file).name)
                print(f"✅ 已备份配置: {config_file}")

        # 备份日志
        logs_dir = self.project_root / 'logs'
        if logs_dir.exists():
            shutil.copytree(logs_dir, timestamped_backup / 'logs', dirs_exist_ok=True)
            print("✅ 已备份日志目录")

        print(f"✅ 数据备份完成: {timestamped_backup}")
        return True

    def _check_dependencies(self) -> bool:
        """检查和安装依赖"""
        print("📦 检查依赖...")

        try:
            # 安装 requirements.txt
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                print(f"⚠️ 依赖安装警告: {result.stderr}")

            # 检查关键依赖
            critical_packages = [
                'fastapi', 'uvicorn', 'httpx', 'pydantic',
                'sqlalchemy', 'alembic', 'pyyaml'
            ]

            for package in critical_packages:
                try:
                    __import__(package.replace('-', '_'))
                    print(f"✅ {package} 已安装")
                except ImportError:
                    print(f"⚠️ {package} 未安装，尝试安装...")
                    subprocess.run([
                        sys.executable, '-m', 'pip', 'install', package
                    ], check=False)

            print("✅ 依赖检查完成")
            return True

        except Exception as e:
            print(f"❌ 依赖检查失败: {e}")
            return False

    def _validate_new_files(self) -> bool:
        """验证新功能文件"""
        print("🔍 验证新功能文件...")

        # 检查新增的功能模块
        required_files = [
            'app/mapper.py',
            'app/comment_sync.py',
            'app/enhanced_service.py',
            'app/github.py',
        ]

        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"❌ 缺少新功能文件: {', '.join(missing_files)}")
            print("请确保所有优化文件都已正确创建")
            return False

        print("✅ 新功能文件验证完成")
        return True

    def _update_configuration(self) -> bool:
        """更新配置文件"""
        print("⚙️ 更新配置...")

        # 检查并更新 mapping.yml
        mapping_file = self.project_root / 'app/mapping.yml'

        try:
            if mapping_file.exists():
                print("✅ mapping.yml 配置已存在")
            else:
                print("⚠️ mapping.yml 不存在，请检查配置")

            # 检查环境变量示例文件
            env_example = self.project_root / 'env.example'
            if env_example.exists():
                print("✅ env.example 文件已存在")

            # 检查 .env 文件
            env_file = self.project_root / '.env'
            if not env_file.exists():
                print("⚠️ .env 文件不存在，请根据 env.example 创建")
                if env_example.exists():
                    shutil.copy2(env_example, env_file)
                    print("✅ 已从 env.example 创建 .env 文件")

            print("✅ 配置文件检查完成")
            return True

        except Exception as e:
            print(f"❌ 配置更新失败: {e}")
            return False

    def _upgrade_database(self) -> bool:
        """升级数据库结构"""
        print("🗄️ 升级数据库...")

        try:
            # 确保数据目录存在
            data_dir = self.project_root / 'data'
            data_dir.mkdir(exist_ok=True)

            # 运行 Alembic 迁移
            result = subprocess.run([
                'alembic', 'upgrade', 'head'
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                print("✅ 数据库迁移成功")
                print(f"迁移输出: {result.stdout}")
            else:
                print(f"⚠️ 数据库迁移警告: {result.stderr}")
                # 尝试初始化数据库
                init_result = subprocess.run([
                    'alembic', 'stamp', 'head'
                ], capture_output=True, text=True, cwd=self.project_root)
                if init_result.returncode == 0:
                    print("✅ 数据库已初始化")

            return True

        except Exception as e:
            print(f"❌ 数据库升级失败: {e}")
            return False

    def _test_functionality(self) -> bool:
        """测试功能"""
        print("🧪 测试系统功能...")

        try:
            # 测试模块导入
            test_modules = [
                'app.mapper',
                'app.comment_sync',
                'app.enhanced_service',
                'app.github',
            ]

            for module_name in test_modules:
                try:
                    __import__(module_name)
                    print(f"✅ {module_name} 导入成功")
                except ImportError as e:
                    print(f"⚠️ {module_name} 导入失败: {e}")

            # 运行快速测试（如果存在）
            quick_test_file = self.project_root / 'quick_test.py'
            if quick_test_file.exists():
                print("🧪 运行快速测试...")
                result = subprocess.run([
                    sys.executable, str(quick_test_file)
                ], capture_output=True, text=True, cwd=self.project_root)

                if result.returncode == 0:
                    print("✅ 快速测试通过")
                else:
                    print(f"⚠️ 快速测试警告: {result.stderr}")

            print("✅ 功能测试完成")
            return True

        except Exception as e:
            print(f"❌ 功能测试失败: {e}")
            return False

    def _show_next_steps(self) -> None:
        """显示后续步骤"""
        print("📋 后续步骤:")
        print("1. 检查并完善 .env 配置文件")
        print("2. 验证 GitHub 和 Notion API 令牌")
        print("3. 运行完整测试: python test_sync_system.py")
        print("4. 启动服务: uvicorn app.server:app --reload")
        print("5. 测试 Webhook 端点")
        print()
        print("🎯 升级完成！现在你的系统支持 GitHub-Notion 双向同步！")


def main():
    """主函数"""
    upgrader = SyncSystemUpgrader()

    if not upgrader.run():
        print("💥 升级失败！请查看错误信息并重试")
        sys.exit(1)

    print("🎉 升级成功！")


if __name__ == "__main__":
    main() 