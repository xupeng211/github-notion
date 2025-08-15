"""github notion bidirectional schema changes

Revision ID: 0e1f2d3c4b5a
Revises: f233e784c02f
Create Date: 2025-08-14 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "0e1f2d3c4b5a"
down_revision = "f233e784c02f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    bind.dialect.name

    # 1) mapping: add new columns for multi-platform support
    with op.batch_alter_table("mapping") as batch:
        batch.add_column(sa.Column("source_platform", sa.String(), nullable=False, server_default="gitee"))
        batch.add_column(sa.Column("source_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("source_url", sa.String(), nullable=True))
        batch.add_column(sa.Column("notion_database_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")))
        batch.add_column(sa.Column("last_sync_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("sync_hash", sa.String(), nullable=True))

    # 2) backfill source_id from legacy issue_id
    cols = [c["name"] for c in inspector.get_columns("mapping")]
    if "issue_id" in cols:
        op.execute("UPDATE mapping SET source_id = issue_id WHERE source_id IS NULL")

    # 3) drop legacy issue_id column if present
    cols = [c["name"] for c in inspector.get_columns("mapping")]
    if "issue_id" in cols:
        with op.batch_alter_table("mapping") as batch:
            batch.drop_column("issue_id")

    # 4) add indexes and unique constraint for new columns
    # Note: do not drop legacy constraints on SQLite to avoid errors; coexist is acceptable after dropping issue_id
    with op.batch_alter_table("mapping") as batch:
        batch.create_index("ix_mapping_source_platform", ["source_platform"])
        batch.create_index("ix_mapping_source_id", ["source_id"])
        batch.create_unique_constraint("uq_mapping_source", ["source_platform", "source_id"])

    # 5) processed_event: add source_platform
    with op.batch_alter_table("processed_event") as batch:
        batch.add_column(sa.Column("source_platform", sa.String(), nullable=False, server_default="gitee"))
        batch.create_index("ix_processed_event_source_platform", ["source_platform"])

    # 6) deadletter: add columns
    with op.batch_alter_table("deadletter") as batch:
        batch.add_column(sa.Column("source_platform", sa.String(), nullable=True))
        batch.add_column(sa.Column("entity_id", sa.String(), nullable=True))

    # 7) create sync_event table
    op.create_table(
        "sync_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_hash", sa.String(), nullable=False),
        sa.Column("source_platform", sa.String(), nullable=False),
        sa.Column("target_platform", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("sync_direction", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("is_sync_induced", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("parent_event_id", sa.String(), nullable=True),
    )
    op.create_index("ix_sync_event_event_id", "sync_event", ["event_id"], unique=True)
    op.create_index("ix_sync_event_event_hash", "sync_event", ["event_hash"])
    op.create_index("ix_sync_event_entity_id", "sync_event", ["entity_id"])

    # 8) create sync_config table
    op.create_table(
        "sync_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_key", sa.String(), nullable=False),
        sa.Column("config_value", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sync_config_config_key", "sync_config", ["config_key"], unique=True)


def downgrade() -> None:
    # Drop sync_config
    op.drop_index("ix_sync_config_config_key", table_name="sync_config")
    op.drop_table("sync_config")

    # Drop sync_event
    op.drop_index("ix_sync_event_entity_id", table_name="sync_event")
    op.drop_index("ix_sync_event_event_hash", table_name="sync_event")
    op.drop_index("ix_sync_event_event_id", table_name="sync_event")
    op.drop_table("sync_event")

    # deadletter: drop added columns
    with op.batch_alter_table("deadletter") as batch:
        for col in ("source_platform", "entity_id"):
            try:
                batch.drop_column(col)
            except Exception:
                pass

    # processed_event: drop column and index
    with op.batch_alter_table("processed_event") as batch:
        try:
            batch.drop_index("ix_processed_event_source_platform")
        except Exception:
            pass
        try:
            batch.drop_column("source_platform")
        except Exception:
            pass

    # mapping: drop new indexes/constraints and columns; restore issue_id
    with op.batch_alter_table("mapping") as batch:
        for idx in ("ix_mapping_source_platform", "ix_mapping_source_id"):
            try:
                batch.drop_index(idx)
            except Exception:
                pass
        try:
            batch.drop_constraint("uq_mapping_source", type_="unique")
        except Exception:
            pass
        # restore legacy column
        batch.add_column(sa.Column("issue_id", sa.String(), nullable=True))
        # drop new columns
        for col in (
            "source_platform",
            "source_id",
            "source_url",
            "notion_database_id",
            "created_at",
            "updated_at",
            "sync_enabled",
            "last_sync_at",
            "sync_hash",
        ):
            try:
                batch.drop_column(col)
            except Exception:
                pass
    # backfill issue_id from source_id if available
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("mapping")]
    if "issue_id" in cols and "source_id" in cols:
        op.execute("UPDATE mapping SET issue_id = source_id WHERE issue_id IS NULL")
