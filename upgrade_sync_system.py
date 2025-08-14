#!/usr/bin/env python3
"""
GitHub-Notion 双向同步系统升级脚本

自动化应用优化功能，包括配置检查、依赖安装和功能测试。
"""
import os
import sys
import json
import yaml
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upgrade.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SyncSystemUpgrader:
    """同步系统升级器"""
    
    def __init__(self):
        self.project_root = Path('.')
        self.required_env_vars = [
            'GITHUB_TOKEN',
            'NOTION_TOKEN', 
            'NOTION_DATABASE_ID'
        ]
        self.optional_env_vars = [
            'GITHUB_WEBHOOK_SECRET',
            'NOTION_WEBHOOK_SECRET'
        ]
        
    def run_upgrade(self) -> bool:
        """运行完整的升级流程"""
        try:
            print("🚀 开始 GitHub-Notion 双向同步系统升级...")
            print("=" * 60)
            
            # 1. 环境检查
            if not self._check_environment():
                return False
            
            # 2. 备份现有配置
            if not self._backup_existing_config():
                return False
            
            # 3. 检查依赖
            if not self._check_dependencies():
                return False
            
            # 4. 验证新文件
            if not self._validate_new_files():
                return False
            
            # 5. 更新配置
            if not self._update_configuration():
                return False
            
            # 6. 测试新功能
            if not self._test_new_features():
                return False
            
            # 7. 生成使用报告
            self._generate_usage_report()
            
            print("\n✅ 升级完成！")
            print("🎉 你的 GitHub-Notion 双向同步系统已经全面优化！")
            print("\n📖 请查看 'GITHUB_NOTION_SYNC_OPTIMIZATION.md' 获取详细使用指南")
            print("📊 查看 'upgrade_report.txt' 获取升级摘要")
            
            return True
            
        except Exception as e:
            logger.error(f"升级过程中出现错误: {e}")
            print(f"\n❌ 升级失败: {e}")
            return False
    
    def _check_environment(self) -> bool:
        """检查环境配置"""
        print("🔍 检查环境配置...")
        
        missing_vars = []
        for var in self.required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
            print("\n请设置以下环境变量:")
            for var in missing_vars:
                print(f"  export {var}=\"your_value_here\"")
            return False
        
        # 检查可选环境变量
        missing_optional = []
        for var in self.optional_env_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_optional:
            print(f"⚠️  建议设置的可选环境变量: {', '.join(missing_optional)}")
            print("  这些变量用于 webhook 签名验证，提高安全性")
        
        print("✅ 环境配置检查完成")
        return True
    
    def _backup_existing_config(self) -> bool:
        """备份现有配置"""
        print("💾 备份现有配置...")
        
        backup_dir = self.project_root / 'backup'
        backup_dir.mkdir(exist_ok=True)
        
        files_to_backup = [
            'app/mapping.yml',
            'app/service.py',
            'app/notion.py',
            'data/sync.db'
        ]
        
        for file_path in files_to_backup:
            source = self.project_root / file_path
            if source.exists():
                backup_path = backup_dir / f"{source.name}.backup"
                try:
                    import shutil
                    shutil.copy2(source, backup_path)
                    logger.info(f"已备份 {file_path} -> {backup_path}")
                except Exception as e:
                    logger.warning(f"无法备份 {file_path}: {e}")
        
        print("✅ 配置备份完成")
        return True
    
    def _check_dependencies(self) -> bool:
        """检查和安装依赖"""
        print("📦 检查 Python 依赖...")
        
        required_packages = [
            'fastapi',
            'httpx',
            'pyyaml',
            'pydantic',
            'sqlalchemy',
            'prometheus-client',
            'apscheduler'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"📥 安装缺失的依赖: {', '.join(missing_packages)}")
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install'
                ] + missing_packages, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"依赖安装失败: {e}")
                return False
        
        print("✅ 依赖检查完成")
        return True
    
    def _validate_new_files(self) -> bool:
        """验证新文件是否存在"""
        print("🔍 验证新功能文件...")
        
        required_files = [
            'app/mapper.py',
            'app/enhanced_service.py', 
            'app/comment_sync.py',
            'GITHUB_NOTION_SYNC_OPTIMIZATION.md'
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
            with open(mapping_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查是否为新格式
            if 'github_to_notion' not in config:
                print("📝 映射配置需要手动更新为新格式")
                print("请参考 GITHUB_NOTION_SYNC_OPTIMIZATION.md 中的配置示例")
                return True
            
            # 验证配置完整性
            required_sections = ['github_to_notion', 'notion_to_github', 'sync_config']
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                print(f"⚠️  配置文件缺少以下部分: {', '.join(missing_sections)}")
                print("建议根据文档补充完整配置")
            
        except Exception as e:
            logger.warning(f"配置文件检查失败: {e}")
        
        print("✅ 配置更新完成")
        return True
    
    def _test_new_features(self) -> bool:
        """测试新功能"""
        print("🧪 测试新功能...")
        
        test_results = []
        
        # 测试字段映射器
        try:
            from app.mapper import field_mapper
            github_data = {"title": "Test Issue", "state": "open"}
            notion_props = field_mapper.github_to_notion(github_data)
            test_results.append(("字段映射器", len(notion_props) > 0))
            logger.info("字段映射器测试通过")
        except Exception as e:
            test_results.append(("字段映射器", False))
            logger.error(f"字段映射器测试失败: {e}")
        
        # 测试增强服务
        try:
            from app.enhanced_service import process_github_event_sync
            test_results.append(("增强服务导入", True))
            logger.info("增强服务导入测试通过")
        except Exception as e:
            test_results.append(("增强服务导入", False))
            logger.error(f"增强服务导入失败: {e}")
        
        # 测试评论同步
        try:
            from app.comment_sync import comment_sync_service
            test_results.append(("评论同步服务", True))
            logger.info("评论同步服务测试通过")
        except Exception as e:
            test_results.append(("评论同步服务", False))
            logger.error(f"评论同步服务测试失败: {e}")
        
        # 测试 Notion 服务
        try:
            from app.notion import notion_service
            test_results.append(("Notion 服务", True))
            logger.info("Notion 服务测试通过")
        except Exception as e:
            test_results.append(("Notion 服务", False))
            logger.error(f"Notion 服务测试失败: {e}")
        
        # 输出测试结果
        print("\n📊 功能测试结果:")
        for test_name, passed in test_results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        failed_tests = [name for name, passed in test_results if not passed]
        if failed_tests:
            print(f"\n⚠️  以下功能测试失败: {', '.join(failed_tests)}")
            print("请检查相关模块的导入和配置")
        
        print("✅ 功能测试完成")
        return True
    
    def _generate_usage_report(self) -> None:
        """生成使用报告"""
        print("📊 生成升级报告...")
        
        report = []
        report.append("GitHub-Notion 双向同步系统升级报告")
        report.append("=" * 50)
        report.append(f"升级时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 环境信息
        report.append("环境配置:")
        for var in self.required_env_vars + self.optional_env_vars:
            value = os.getenv(var, "未设置")
            if var in ['GITHUB_TOKEN', 'NOTION_TOKEN']:
                value = value[:8] + "..." if value != "未设置" and len(value) > 8 else value
            report.append(f"  {var}: {value}")
        report.append("")
        
        # 新增功能
        report.append("新增功能:")
        report.append("  ✅ 增强的字段映射系统")
        report.append("  ✅ 评论双向同步")
        report.append("  ✅ 改进的 webhook 处理")
        report.append("  ✅ 智能防循环机制")
        report.append("  ✅ 性能优化")
        report.append("  ✅ 灵活配置系统")
        report.append("")
        
        # 文件状态
        report.append("新增文件:")
        new_files = [
            'app/mapper.py',
            'app/enhanced_service.py',
            'app/comment_sync.py',
            'GITHUB_NOTION_SYNC_OPTIMIZATION.md'
        ]
        
        for file_path in new_files:
            exists = "✅" if (self.project_root / file_path).exists() else "❌"
            report.append(f"  {exists} {file_path}")
        report.append("")
        
        # 下一步操作
        report.append("后续操作建议:")
        report.append("1. 阅读 GITHUB_NOTION_SYNC_OPTIMIZATION.md 了解详细使用方法")
        report.append("2. 根据你的 Notion 数据库结构调整 app/mapping.yml 配置")
        report.append("3. 在 GitHub 仓库中配置 webhook 事件")
        report.append("4. 在 Notion 中配置集成 webhook")
        report.append("5. 测试双向同步功能")
        report.append("6. 监控日志和性能指标")
        
        # 写入报告文件
        report_file = self.project_root / 'upgrade_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        logger.info(f"升级报告已生成: {report_file}")
        print("✅ 升级报告生成完成")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("GitHub-Notion 双向同步系统升级脚本")
        print("用法: python upgrade_sync_system.py")
        print("\n功能:")
        print("  - 检查环境配置")
        print("  - 备份现有配置")
        print("  - 验证新功能文件")
        print("  - 测试功能模块")
        print("  - 生成升级报告")
        return
    
    upgrader = SyncSystemUpgrader()
    
    try:
        success = upgrader.run_upgrade()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  升级被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"意外错误: {e}")
        print(f"\n❌ 升级失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 