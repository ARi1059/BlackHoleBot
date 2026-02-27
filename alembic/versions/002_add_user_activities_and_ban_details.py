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
    # 1. 扩展 users 表 - 添加封禁相关字段
    op.add_column('users', sa.Column('banned_reason', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('banned_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('banned_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_banned_by', 'users', 'users', ['banned_by'], ['id'])

    # 2. 创建 user_activities 表
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

    # 3. 创建索引
    op.create_index('idx_user_activities_user_time', 'user_activities', ['user_id', 'created_at'])
    op.create_index('idx_user_activities_type', 'user_activities', ['activity_type', 'created_at'])
    op.create_index('idx_user_activities_collection', 'user_activities', ['collection_id', 'created_at'])
    op.create_index(op.f('ix_user_activities_id'), 'user_activities', ['id'], unique=False)
    op.create_index(op.f('ix_user_activities_user_id'), 'user_activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_activities_activity_type'), 'user_activities', ['activity_type'], unique=False)
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
