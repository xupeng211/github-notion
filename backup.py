#!/usr/bin/env python3

"""
备份脚本，用于定期备份应用数据和配置到 AWS S3
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self, bucket_name, region_name="ap-northeast-1"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=region_name)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def backup_file(self, file_path: Path, prefix: str = ""):
        """备份单个文件到 S3"""
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        try:
            s3_key = f"{prefix}/{self.timestamp}/{file_path.name}"
            self.s3_client.upload_file(str(file_path), self.bucket_name, s3_key)
            logger.info(f"Successfully backed up {file_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to backup {file_path}: {e}")
            return False

    def backup_env_vars(self, env_file: Path):
        """备份环境变量"""
        if not env_file.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return False

        try:
            s3_key = f"env_vars/{self.timestamp}/env_backup"
            self.s3_client.upload_file(str(env_file), self.bucket_name, s3_key)
            logger.info(f"Successfully backed up environment variables to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to backup environment variables: {e}")
            return False

    def cleanup_old_backups(self, prefix: str, keep_days: int = 30):
        """清理旧的备份文件"""
        try:
            # 列出所有备份
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)

            if "Contents" not in response:
                return

            # 获取当前时间
            now = datetime.now()

            # 遍历并删除过期的备份
            for obj in response["Contents"]:
                # 从对象键中提取时间戳
                try:
                    backup_date = datetime.strptime(obj["Key"].split("/")[1], "%Y%m%d_%H%M%S")
                    # 如果备份超过保留天数，则删除
                    if (now - backup_date).days > keep_days:
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj["Key"])
                        logger.info(f"Deleted old backup: {obj['Key']}")
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse date from key: {obj['Key']}")
                    continue

        except ClientError as e:
            logger.error(f"Failed to cleanup old backups: {e}")


def main():
    """主函数"""
    # 获取环境变量
    bucket_name = os.getenv("BACKUP_BUCKET_NAME")
    if not bucket_name:
        logger.error("BACKUP_BUCKET_NAME environment variable not set")
        return 1

    # 初始化备份管理器
    backup_mgr = BackupManager(bucket_name)

    # 要备份的文件列表
    files_to_backup = [
        Path(".env"),
        Path("docker-compose.yml"),
        Path("Dockerfile"),
        Path("requirements.txt"),
        Path("prometheus.yml"),
        Path("cloudwatch-config.json"),
        Path("waf-rules.json"),
    ]

    # 备份配置文件
    for file_path in files_to_backup:
        backup_mgr.backup_file(file_path, prefix="config")

    # 备份环境变量
    backup_mgr.backup_env_vars(Path(".env"))

    # 清理旧备份
    backup_mgr.cleanup_old_backups("config/", keep_days=30)
    backup_mgr.cleanup_old_backups("env_vars/", keep_days=30)

    logger.info("Backup completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
