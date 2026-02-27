"""add broadcast_logs table

Revision ID: 003
Revises: 002
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    # 检查表是否已存在
    existing_tables = inspector.get_table_names()

    if 'broadcast_logs' not in existing_tables:
        op.create_table(
            'broadcast_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('admin_id', sa.Integer(), nullable=False),
            sa.Column('message_type', sa.String(length=20), nullable=False),
            sa.Column('message_text', sa.Text(), nullable=True),
            sa.Column('file_id', sa.String(length=255), nullable=True),
            sa.Column('has_buttons', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('total_users', sa.Integer(), nullable=False),
            sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

        # 创建索引
        op.create_index('idx_broadcast_logs_admin', 'broadcast_logs', ['admin_id', 'started_at'])
        op.create_index(op.f('ix_broadcast_logs_id'), 'broadcast_logs', ['id'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index(op.f('ix_broadcast_logs_id'), table_name='broadcast_logs')
    op.drop_index('idx_broadcast_logs_admin', table_name='broadcast_logs')

    # 删除表
    op.drop_table('broadcast_logs')
