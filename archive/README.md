# Archived files

This directory contains files that were present in earlier iterations of the project but are no longer part of the primary runtime path. They are kept here temporarily for reference and potential future reuse.

- app/main.py: Legacy FastAPI entrypoint with a separate metrics wiring and custom logging. The current entry is `app/server.py`.
- app/db.py: Early SQLite direct-access helper. The project has migrated to SQLAlchemy models in `app/models.py`.

If these files are not needed after verification and soak time, consider deleting them permanently.

# 归档说明

本目录用于存放历史实现与迁移资料。

- `gitee-notion-sync/app.py`：早期 Flask 版本的服务端，已被 FastAPI (`app/server.py`) 取代。
- 当前生产镜像与文档均基于 FastAPI。请勿在新代码中引用此旧实现。
- 如需参考旧实现逻辑，请在本目录阅读并避免改动生产路径。


