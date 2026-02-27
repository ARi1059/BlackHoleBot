"""add user_activities table and ban details

Revision ID: 002
Revises: 001
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import text, inspect

    connection = op.get_bind()
    inspector = inspect(connection)

    # 1. 扩展 users 表 - 添加封禁相关字段（检查列是否存在）
    existing_columns = [col['name'] for col in inspector.get_columns('users')]

    if 'banned_reason' not in existing_columns:
        op.add_column('users', sa.Column('banned_reason', sa.Text(), nullable=True))
    if 'banned_at' not in existing_columns:
        op.add_column('users', sa.Column('banned_at', sa.DateTime(), nullable=True))
    if 'banned_by' not in existing_columns:
        op.add_column('users', sa.Column('banned_by', sa.Integer(), nullable=True))

    # 检查外键是否存在
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('users')]
    if 'fk_users_banned_by' not in existing_fks:
        op.create_foreign_key('fk_users_banned_by', 'users', 'users', ['banned_by'], ['id'])

    # 2. 创建 user_activities 表（检查表是否存在）
    existing_tables = inspector.get_table_names()

    if 'user_activities' not in existing_tables:
        op.create_table(
            'user_activities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('activity_type', sa.String(length=50), nullable=False),
            sa.Column('collection_id', sa.Integer(), nullable=True),
            sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 3. 创建索引（检查索引是否存在）
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('user_activities')]

    if 'idx_user_activities_user_time' not in existing_indexes:
        op.create_index('idx_user_activities_user_time', 'user_activities', ['user_id', 'created_at'])
    if 'idx_user_activities_type' not in existing_indexes:
        op.create_index('idx_user_activities_type', 'user_activities', ['activity_type', 'created_at'])
    if 'idx_user_activities_collection' not in existing_indexes:
        op.create_index('idx_user_activities_collection', 'user_activities', ['collection_id', 'created_at'])
    if 'ix_user_activities_id' not in existing_indexes:
        op.create_index(op.f('ix_user_activities_id'), 'user_activities', ['id'], unique=False)
    if 'ix_user_activities_user_id' not in existing_indexes:
        op.create_index(op.f('ix_user_activities_user_id'), 'user_activities', ['user_id'], unique=False)
    if 'ix_user_activities_activity_type' not in existing_indexes:
        op.create_index(op.f('ix_user_activities_activity_type'), 'user_activities', ['activity_type'], unique=False)
    if 'ix_user_activities_created_at' not in existing_indexes:
        op.create_index(op.f('ix_user_activities_created_at'), 'user_activities', ['created_at'], unique=False)


def downgrade() -> None:
    # 删除 user_activities 表及其索引
    op.drop_index(op.f('ix_user_activities_created_at'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_activity_type'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_user_id'), table_name='user_activities')
    op.drop_index(op.f('ix_user_activities_id'), table_name='user_activities')
    op.drop_index('idx_user_activities_collection', table_name='user_activities')
    op.drop_index('idx_user_activities_type', table_name='user_activities')
    op.drop_index('idx_user_activities_user_time', table_name='user_activities')
    op.drop_table('user_activities')

    # 删除 users 表的封禁相关字段
    op.drop_constraint('fk_users_banned_by', 'users', type_='foreignkey')
    op.drop_column('users', 'banned_by')
    op.drop_column('users', 'banned_at')
    op.drop_column('users', 'banned_reason')
