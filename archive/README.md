# Archived files

This directory contains files that were present in earlier iterations of the project but are no longer part of the primary runtime path. They are kept here temporarily for reference and potential future reuse.

- app/main.py: Legacy FastAPI entrypoint with a separate metrics wiring and custom logging. The current entry is `app/server.py`.
- app/db.py: Early SQLite direct-access helper. The project has migrated to SQLAlchemy models in `app/models.py`.

If these files are not needed after verification and soak time, consider deleting them permanently.


