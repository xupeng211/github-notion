from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '8f2c0b7a3f12'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'mapping',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('issue_id', sa.String(), nullable=False),
        sa.Column('notion_page_id', sa.String(), nullable=False),
        sa.UniqueConstraint('issue_id', name='uq_mapping_issue_id'),
        sa.UniqueConstraint('notion_page_id', name='uq_mapping_notion_page_id'),
    )
    op.create_index('ix_mapping_issue_id', 'mapping', ['issue_id'], unique=False)
    op.create_index('ix_mapping_notion_page_id', 'mapping', ['notion_page_id'], unique=False)

    op.create_table(
        'deadletter',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='failed'),
    )

    op.create_table(
        'processed_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_hash', sa.String(), nullable=False),
        sa.Column('issue_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.UniqueConstraint('event_hash', name='uq_processed_event_event_hash'),
    )
    op.create_index('ix_processed_event_event_hash', 'processed_event', ['event_hash'], unique=False)
    op.create_index('ix_processed_event_issue_id', 'processed_event', ['issue_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_processed_event_issue_id', table_name='processed_event')
    op.drop_index('ix_processed_event_event_hash', table_name='processed_event')
    op.drop_table('processed_event')

    op.drop_table('deadletter')

    op.drop_index('ix_mapping_notion_page_id', table_name='mapping')
    op.drop_index('ix_mapping_issue_id', table_name='mapping')
    op.drop_table('mapping') 